from core import env_check
from common.paths import model_file, app_root, results_dir
from common.logger import log_info, log_warning, log_error
import numpy as np
import joblib
from pathlib import Path
import argparse
import json
import os
import sys

# Bootstrap: garantir que a raiz do projeto esteja no sys.path
_base_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.abspath(os.path.join(_base_dir, '..'))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)


def _maybe_load_env():
    """Carrega variáveis de ambiente via python-dotenv, se disponível (import dinâmico)."""
    try:
        import importlib.util
        import importlib
        spec = importlib.util.find_spec('dotenv')
        if spec is None:
            return
        dotenv = importlib.import_module('dotenv')
        load_dotenv = getattr(dotenv, 'load_dotenv', None)
        if not load_dotenv:
            return
        env_path = Path(app_root()) / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=str(env_path))
            log_info(f"Variáveis .env carregadas de {env_path}")
    except Exception:
        # silencioso
        pass


def validate_payload(payload: dict) -> list:
    """Valida estrutura mínima do payload do modelo.
    Retorna lista de problemas encontrados (vazia se OK).
    """
    problems = []
    for k in ("model", "features", "scaler", "imputer"):
        if k not in payload:
            problems.append(f"Chave ausente no payload: {k}")
    feats = payload.get("features")
    if not isinstance(feats, (list, tuple)) or len(feats) == 0:
        problems.append("Lista de features inválida ou vazia")
    return problems


def ensure_model_ready(explicit_path: str | None = None) -> tuple[bool, str | None]:
    """Verifica se o modelo pode ser carregado e se dependências básicas estão OK.
    Retorna (ok, mensagem_erro_opcional).
    """
    # Checagem de ambiente
    issues = env_check.check_packages()
    if issues:
        log_warning("Problemas de ambiente detectados:")
        for i in issues:
            log_warning(f" - {i}")
        # Não bloqueia totalmente; apenas informa

    # Caminho do modelo
    try:
        path = Path(explicit_path) if explicit_path else Path(model_file())
        if not path.exists():
            msg = f"Modelo não encontrado em {path}"
            log_warning(msg)
            return False, msg
        payload = joblib.load(path)
        probs = validate_payload(payload)
        if probs:
            msg = "; ".join(probs)
            log_error(f"Payload inválido: {msg}")
            return False, msg
        log_info(f"Modelo carregado com sucesso de {path}")
        return True, None
    except Exception as e:
        msg = f"Falha ao carregar modelo: {e}"
        log_error(msg)
        return False, msg


def latest_model_info() -> dict:
    """Lê manifest.json do diretório do modelo e retorna último registro se existir."""
    try:
        from common.paths import app_root
        dirp = Path(app_root()) / "model"
        man = dirp / "manifest.json"
        if not man.exists():
            return {}
        entries = json.load(open(man, "r", encoding="utf-8"))
        if not entries:
            return {}
        return entries[-1]
    except Exception:
        return {}


def load_model_payload(path: Path | None) -> dict:
    """Carrega payload do modelo (joblib)."""
    try:
        if path is None:
            path = Path(model_file())
        if not path.exists():
            raise FileNotFoundError(f"Modelo não encontrado em {path}")
        payload = joblib.load(path)
        # valida payload esperado
        for k in ("model", "features", "scaler", "imputer"):
            if k not in payload:
                raise ValueError(f"Payload inválido; chave ausente: {k}")
        return payload
    except Exception as e:
        log_error(f"Falha ao carregar modelo: {e}")
        raise


def features_from_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def features_from_video(video_path: Path) -> dict:
    """Extrator de vídeo desativado.

    O fluxo atual trabalha com features pré-calculadas (JSON/CSV/Parquet).
    Para extrair de vídeo, integrar um módulo `tools/extract_features.py` moderno
    ou gerar CSVs e usar `--dataset`/`--features-json`.
    """
    raise NotImplementedError(
        "Extração de features de vídeo indisponível. Use --features-json ou --dataset.")


def vectorize_features(feat_dict: dict, feature_cols: list, imputer, scaler) -> np.ndarray:
    """Ordena e transforma features conforme treino."""
    try:
        vals = []
        for c in feature_cols:
            v = feat_dict.get(c, np.nan)
            vals.append(float(v) if v is not None else np.nan)
        X = np.array([vals], dtype=np.float64)
        X_imp = imputer.transform(X)
        X_scl = scaler.transform(X_imp)
        return X_scl
    except Exception as e:
        log_error(f"Falha ao preparar vetor de features: {e}")
        raise


def predict(payload: dict, X_scl: np.ndarray) -> dict:
    """Realiza previsão com OneClassSVM e retorna resultado legível."""
    try:
        model = payload["model"]
        pred = int(model.predict(X_scl)[0])  # +1 ou -1
        score = float(model.decision_function(X_scl)[0])
        result = {
            "biomechanical_valid": (pred == 1),
            "raw_pred": pred,
            "score": score
        }
        return result
    except Exception as e:
        log_error(f"Falha na previsão: {e}")
        raise


def main():
    _maybe_load_env()
    ap = argparse.ArgumentParser(
        description="Executa previsões usando modelo treinado")
    ap.add_argument("--config", default=str(Path(app_root()) / "config" /
                    "pipeline.json"), help="Arquivo JSON de configuração opcional")
    ap.add_argument("--model", default=os.environ.get("MODEL_PATH", ""),
                    help="Caminho do modelo (.pkl/.joblib); padrão usa common.paths.model_file()")
    ap.add_argument("--video", help="Vídeo para extrair features e prever")
    ap.add_argument("--features-json",
                    help="Arquivo JSON com features já calculadas")
    ap.add_argument(
        "--dataset", help="Arquivo CSV/Parquet com features para benchmark em lote")
    ap.add_argument("--label-col", default=os.environ.get("LABEL_COL",
                    "label"), help="Nome da coluna de rótulo para métricas (opcional)")
    ap.add_argument("--save-results", action="store_true",
                    help="Salva métricas do benchmark em results_oneclass/evaluation_results.json")
    args = ap.parse_args()

    # Carrega config opcional
    cfg = {}
    cfg_path = Path(args.config)
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            log_info(f"Config carregada de {cfg_path}")
        except Exception as e:
            log_warning(f"Falha ao ler config {cfg_path}: {e}")

    model_path = Path(args.model) if args.model else None
    # Check de modelo e dependências antes de carregar
    ok, err = ensure_model_ready(str(model_path) if model_path else None)
    if not ok:
        log_error(f"Modelo não pronto: {err}")
        sys.exit(2)
    payload = load_model_payload(model_path)
    feature_cols = payload["features"]
    imputer = payload["imputer"]
    scaler = payload["scaler"]

    # Benchmark em lote, se dataset fornecido
    if args.dataset:
        import pandas as pd
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        ds_path = Path(args.dataset)
        # carregar dataset com colunas necessárias apenas
        cols_needed = list(feature_cols)
        if args.label_col:
            cols_needed = list(set(cols_needed + [args.label_col]))
        if ds_path.suffix.lower() == '.csv':
            try:
                df = pd.read_csv(ds_path, usecols=lambda c: c in cols_needed)
            except Exception:
                df = pd.read_csv(ds_path)
        elif ds_path.suffix.lower() in ('.parquet', '.pq'):
            try:
                df = pd.read_parquet(
                    ds_path, columns=[c for c in cols_needed if c])
            except Exception:
                df = pd.read_parquet(ds_path)
        else:
            log_error(f"Formato não suportado: {ds_path.suffix}")
            sys.exit(2)
        # preparar X e y usando exatamente as colunas de treino salvas
        X_df = df.reindex(columns=feature_cols)
        X = X_df.to_numpy(dtype=float)
        y = df[args.label_col].astype(int).to_numpy(
        ) if args.label_col in df.columns else None
        # transformar
        X_imp = imputer.transform(X)
        X_scl = scaler.transform(X_imp)
        # prever
        raw = payload["model"].predict(X_scl)
        scores = payload["model"].decision_function(X_scl)
        metrics = {}
        if y is not None:
            y_mapped = np.where(y == 1, 1, -1)
            metrics = {
                "accuracy": float(accuracy_score(y_mapped, raw)),
                "precision": float(precision_score(y_mapped, raw, pos_label=1, zero_division=0)),
                "recall": float(recall_score(y_mapped, raw, pos_label=1, zero_division=0)),
                "f1": float(f1_score(y_mapped, raw, pos_label=1, zero_division=0)),
            }
        else:
            metrics = {
                "score_mean": float(np.mean(scores)),
                "score_std": float(np.std(scores)),
                "score_min": float(np.min(scores)),
                "score_max": float(np.max(scores)),
            }
        out = {"dataset": str(ds_path), "metrics": metrics}
        log_info(json.dumps(out))
        # salva resultados se solicitado
        if args.save_results:
            try:
                resdir = Path(results_dir())
                resdir.mkdir(parents=True, exist_ok=True)
                out_path = resdir / "evaluation_results.json"
                with open(out_path, "w", encoding="utf-8") as fh:
                    json.dump(out, fh, ensure_ascii=False, indent=2)
                log_info(f"Resultados salvos em {out_path}")
            except Exception as e:
                log_warning(f"Falha ao salvar resultados: {e}")
        print(json.dumps(out, ensure_ascii=False))
        return

    # Previsão simples
    feat = None
    if args.features_json:
        feat = features_from_json(Path(args.features_json))
        source = f"json:{args.features_json}"
    else:
        log_error(
            "Necessário fornecer --features-json ou --dataset (vídeo desativado)")
        sys.exit(2)

    X_scl = vectorize_features(feat, feature_cols, imputer, scaler)
    res = predict(payload, X_scl)

    log_info(json.dumps({"source": source, "result": res}))
    print(json.dumps({"source": source, "result": res}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error(f"Execução do modelo falhou: {e}")
        sys.exit(1)
