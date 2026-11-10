import os
import sys
import json
import time
from pathlib import Path
import argparse
import subprocess
import itertools
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.svm import OneClassSVM
from common.logger import log_info, log_warning, log_error
from common.paths import app_root


def _load_config(cfg_path: Path) -> dict:
    try:
        if cfg_path.exists():
            with open(cfg_path, 'r', encoding='utf-8') as fh:
                return json.load(fh)
    except Exception as e:
        log_warning(f"Falha ao ler config {cfg_path}: {e}")
    return {
        "data": {
            "train_path": "latest",
            "label_col": "label",
            "ignore_cols": ["video", "filename", "file", "path", "exercise"],
        },
        "training": {
            "algorithm": "oneclass_svm",
            "optimize": True,
            "param_grid": {"nu": [0.01, 0.05, 0.1], "gamma": ["scale", "auto"], "kernel": ["rbf"]},
        },
        "serialization": {"format": "joblib", "output_dir": "model", "versioned": True},
    }


def _latest_dataset_path(root: Path) -> Path | None:
    base = root / "dataset" / "processed_oneclass"
    if not base.exists():
        return None
    candidates: list[Path] = []
    for suf in ("*.parquet", "*.pq", "*.csv", "*.npz", "*.npy", "*.h5", "*.hdf5"):
        candidates.extend(base.glob(suf))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _load_dataset(path: Path, label_col: str, ignore_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    elif ext in (".npz", ".npy"):
        arr = np.load(path)
        if isinstance(arr, np.lib.npyio.NpzFile):
            if "features" in arr:
                df = pd.DataFrame(arr["features"])
            else:
                keys = list(arr.keys())
                df = pd.DataFrame(arr[keys[0]])
        else:
            df = pd.DataFrame(arr)
    elif ext in (".h5", ".hdf5"):
        import h5py  # type: ignore
        with h5py.File(path, "r") as f:
            key = next(iter(f.keys()))
            data = f[key][...]
            df = pd.DataFrame(data)
    else:
        raise ValueError(f"Formato não suportado: {ext}. Formatos aceitos: .csv, .parquet/.pq, .npz/.npy, .h5/.hdf5")

    cols = [c for c in df.columns if c not in set((label_col or "").strip() and [label_col] or []) and c not in set(ignore_cols or [])]
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        raise ValueError("Nenhuma coluna numérica para treino")
    return df, num_cols


def _fit_preprocess(df: pd.DataFrame, feature_cols: list[str]) -> tuple[np.ndarray, SimpleImputer, StandardScaler]:
    X = df.reindex(columns=feature_cols).to_numpy(dtype=float)
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    X_imp = imputer.fit_transform(X)
    X_scl = scaler.fit_transform(X_imp)
    return X_scl, imputer, scaler


def _train_oneclass(X_scl: np.ndarray, grid: dict) -> OneClassSVM:
    combos = list(itertools.product(grid.get("nu", [0.05]), grid.get("gamma", ["scale"]), grid.get("kernel", ["rbf"])) )
    best = None
    best_score = -1e9
    for nu, gamma, kernel in combos:
        try:
            mdl = OneClassSVM(nu=float(nu), gamma=gamma, kernel=kernel)
            mdl.fit(X_scl)
            scores = mdl.decision_function(X_scl)
            score = float(np.mean(scores))
            if score > best_score:
                best_score = score
                best = mdl
        except Exception:
            continue
    return best or OneClassSVM(kernel="rbf", gamma="scale", nu=0.05).fit(X_scl)


def _save_payload(model, features: list[str], imputer: SimpleImputer, scaler: StandardScaler, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"model": model, "features": features, "scaler": scaler, "imputer": imputer}
    alias = out_dir / "model.pkl"
    joblib.dump(payload, alias)
    ts = time.strftime("%Y%m%d-%H%M%S")
    ver = out_dir / f"model-{ts}.pkl"
    joblib.dump(payload, ver)
    try:
        man = out_dir / "manifest.json"
        entries = []
        if man.exists():
            entries = json.load(open(man, "r", encoding="utf-8"))
        entries.append({"created_at": ts, "path": str(ver.name)})
        with open(man, "w", encoding="utf-8") as fh:
            json.dump(entries, fh, ensure_ascii=False, indent=2)
    except Exception as e:
        log_warning(f"Falha ao atualizar manifest: {e}")
    return alias


def main():
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("--input-dir")
        ap.add_argument("--dataset-file")
        args = ap.parse_args()
        root = Path(app_root())
        cfg = _load_config(root / "config" / "pipeline.json")
        train_path = cfg.get("data", {}).get("train_path", "latest")
        label_col = cfg.get("data", {}).get("label_col", "label")
        ignore_cols = cfg.get("data", {}).get("ignore_cols", [])
        optimize = bool(cfg.get("training", {}).get("optimize", True))
        grid = cfg.get("training", {}).get("param_grid", {})

        log_info("Iniciando treinamento do modelo OneClassSVM")
        log_info(json.dumps({"input": train_path, "out": "model\\model.pkl", **{k: v for k, v in grid.items()}}, ensure_ascii=False))

        if args.dataset_file:
            ds = Path(args.dataset_file)
            train_path = str(ds)
        elif args.input_dir:
            inp = Path(args.input_dir)
            meta_dir = root / "dataset" / "metadata"
            meta_dir.mkdir(parents=True, exist_ok=True)
            csvp = meta_dir / "video_metadata.csv"
            jsonp = meta_dir / "video_metadata.json"
            try:
                from core.training_pipeline import extract_video_metadata
                df_meta = extract_video_metadata(inp, csvp, jsonp)
                ds = csvp
                train_path = str(ds)
            except Exception:
                ds = _latest_dataset_path(root)
        else:
            if str(train_path).lower() == "latest":
                ds = _latest_dataset_path(root)
            else:
                ds = (root / str(train_path)).resolve()

        if not ds or not Path(ds).exists():
            raise ValueError("Dataset não encontrado para treino")
        log_info(f"Carregando dataset: {ds}")

        df, feature_cols = _load_dataset(Path(ds), label_col, ignore_cols)
        X_scl, imputer, scaler = _fit_preprocess(df, feature_cols)

        if optimize and grid:
            model = _train_oneclass(X_scl, grid)
        else:
            model = OneClassSVM(kernel="rbf", gamma="scale", nu=0.05)
            model.fit(X_scl)

        out_dir = root / "model"
        alias = _save_payload(model, feature_cols, imputer, scaler, out_dir)
        log_info(f"Modelo salvo em {alias}")
        print(json.dumps({"model_path": str(alias), "features": feature_cols}, ensure_ascii=False))
    except Exception as e:
        log_error(f"Treinamento falhou: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()