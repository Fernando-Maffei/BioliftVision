import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

# Bootstrap: garantir que a raiz do projeto esteja no sys.path
_base_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.abspath(os.path.join(_base_dir, '..'))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

from common.paths import app_root
from core.keypoints import OptimizedKeypointExtractor
from core.adaptive_training import split_dataset_by_exercise, save_exercise_datasets, write_session_index


def normalize_exercise_name(name: str) -> str:
    n = (name or '').lower()
    if 'agachamento' in n or 'squat' in n:
        return 'squat'
    if 'terra' in n or 'deadlift' in n:
        return 'deadlift'
    return 'unknown'


def extract_from_folder(exercise_folder: Path) -> pd.DataFrame:
    ex_name = normalize_exercise_name(exercise_folder.name)
    exts = {'.mp4', '.avi', '.mov', '.mkv'}
    extractor = OptimizedKeypointExtractor(max_workers=4)
    dfs = []
    for video in exercise_folder.rglob('*'):
        if video.suffix.lower() not in exts:
            continue
        try:
            import cv2
            cap = cv2.VideoCapture(str(video))
            if not cap.isOpened():
                print(f"[AVISO] Não foi possível abrir {video}")
                continue
            frames = []
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
            # Capturar mais amostras para movimentos rápidos do Terra
            stride = max(fps // 5, 6)
            max_frames = 240
            idx = 0
            while len(frames) < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                if idx % stride == 0:
                    frames.append(frame)
                idx += 1
            cap.release()
            if not frames:
                print(f"[AVISO] Sem frames válidos: {video}")
                continue
            lms = extractor.extract_landmarks_batch(frames)
            if not lms:
                print(f"[AVISO] Sem landmarks detectados: {video}")
                continue
            df = extractor.calculate_movement_features(lms)
            try:
                df = extractor.add_angle_features(df, ex_name)
            except Exception:
                print(f"[AVISO] Falha ao adicionar ângulos: {video}")
            essential = [c for c in ['knee_angle','hip_angle','torso_angle'] if c in df.columns]
            if essential:
                before = len(df)
                df = df.dropna(subset=essential)
                after = len(df)
                if after == 0:
                    print(f"[AVISO] Linhas essenciais ausentes após limpeza: {video} (removidas {before})")
            df['exercise'] = ex_name
            df['label'] = 1
            df['video_file'] = str(video)
            print(f"[INFO] Extraído {len(df)} linhas de {video.name}")
            dfs.append(df)
        except Exception as e:
            print(f"[ERRO] {video}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def main(exercise: str = 'terra') -> int:
    root = Path(app_root())
    base = root / 'dataset' / 'Exercicios'
    # Resolver pasta pelo nome
    target = None
    for cand in ['Terra', 'Deadlift', exercise]:
        p = base / cand
        if p.exists():
            target = p
            break
    if target is None:
        print(f"[ERRO] Pasta do exercício não encontrada em {base} (terra/deadlift)")
        return 2
    print(f"[INFO] Processando vídeos em: {target}")
    df_new = extract_from_folder(target)
    if df_new.empty:
        print("[AVISO] Nenhum dado extraído; verifique vídeos e enquadramento corporal.")
        return 3
    processed_dir = root / 'dataset' / 'processed_oneclass'
    processed_dir.mkdir(parents=True, exist_ok=True)
    # Salvar somente por exercício
    splits = split_dataset_by_exercise(df_new, exercise_col='exercise')
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    ex_paths = save_exercise_datasets(processed_dir, session_id, splits)
    idx = processed_dir / f'session_index_{session_id}.json'
    write_session_index(idx, {
        'session_id': session_id,
        'combined_path': None,
        'exercise_paths': ex_paths,
        'counts': {k: int(v.shape[0]) for k, v in splits.items()},
        'created_at': datetime.now().isoformat(timespec='seconds')
    })
    print("[INFO] Arquivos por exercício gerados:")
    for k, p in ex_paths.items():
        print(f" - {k}: {p}")
    return 0


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'terra'
    sys.exit(main(arg))