import cv2
import mediapipe as mp
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import os
from concurrent.futures import ThreadPoolExecutor
import time
from pathlib import Path
from core.angulos import AdvancedAngleCalculator


class OptimizedKeypointExtractor:
    """
    Extrator otimizado de keypoints com processamento paralelo
    """

    def __init__(self, max_workers: int = 4):
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.max_workers = max_workers
        self.landmark_cache = {}
        self.angle_calculator = AdvancedAngleCalculator()

    def extract_landmarks_batch(self, frames: List[np.ndarray]) -> List[Dict]:
        """Extrai landmarks de múltiplos frames com melhor tratamento de erros"""
        results = []

      
        for i, frame in enumerate(frames):
            try:
                
                timestamp_ms = int(i * (1000 / 30))
                result = self._process_single_frame(frame, timestamp_ms)
                if result is not None:
                    results.append(result)
                else:
                    # Adicionar entrada vazia para manter sincronização temporal
                    print(f"Frame {i}: Nenhum landmark detectado")
            except Exception as e:
                print(f"Erro processando frame {i}: {e}")
                continue

        return results

    def _process_single_frame(self, frame: np.ndarray, timestamp_ms: int = None) -> Optional[Dict]:
        """Processa frame único otimizado com timestamp adequado"""
        try:
            # Redimensiona para performance (mantém aspect ratio)
            h, w = frame.shape[:2]
            if w > 640:  # Limita largura máxima
                scale = 640 / w
                new_w, new_h = 640, int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Criar uma nova instância do pose para cada frame para evitar problemas de timestamp
            with mp.solutions.pose.Pose(
                static_image_mode=True,  # Processa cada frame independentemente
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            ) as pose_processor:
                results = pose_processor.process(frame_rgb)

            if not results.pose_landmarks:
                return None

            return self._extract_landmarks_optimized(results.pose_landmarks.landmark)

        except Exception as e:
            print(f"Erro no processamento do frame: {e}")
            return None

    def _extract_landmarks_optimized(self, landmarks) -> Dict:
        keypoints = {}
        landmark_indices = {
            0: "NOSE", 7: "LEFT_EAR", 8: "RIGHT_EAR",
            11: "LEFT_SHOULDER", 12: "RIGHT_SHOULDER",
            23: "LEFT_HIP", 24: "RIGHT_HIP",
            25: "LEFT_KNEE", 26: "RIGHT_KNEE",
            27: "LEFT_ANKLE", 28: "RIGHT_ANKLE"
        }

        for idx, name in landmark_indices.items():
            if idx < len(landmarks):
                landmark = landmarks[idx]
                keypoints[f"{name}_x"] = landmark.x
                keypoints[f"{name}_y"] = landmark.y
                keypoints[f"{name}_z"] = landmark.z
                keypoints[f"{name}_visibility"] = landmark.visibility
            else:
                keypoints.update({f"{name}_{coord}": 0.0 for coord in [
                                 'x', 'y', 'z', 'visibility']})

        return keypoints

    def calculate_movement_features(self, landmarks_sequence: List[Dict]) -> pd.DataFrame:
        """Calcula features de movimento da sequência"""
        if not landmarks_sequence:
            return pd.DataFrame()

        df = pd.DataFrame(landmarks_sequence)

        # Remover frames completamente nulos
        df = df.dropna(how='all')
        if df.empty:
            return df

        # Features de velocidade
        for point in ['LEFT_HIP', 'RIGHT_HIP', 'LEFT_SHOULDER']:
            for coord in ['x', 'y']:
                col = f"{point}_{coord}"
                if col in df.columns:
                    df[f"{point}_{coord}_velocity"] = df[col].diff()
                    df[f"{point}_{coord}_acceleration"] = df[f"{point}_{coord}_velocity"].diff()

        # Features de estabilidade
        df['torso_stability'] = self._calculate_torso_stability(df)
        df['balance_index'] = self._calculate_balance_index(df)

        # Pequeno suavizador para reduzir ruído em diferenças
        for c in df.columns:
            if c.endswith('_velocity') or c.endswith('_acceleration'):
                try:
                    df[c] = df[c].rolling(window=3, min_periods=1).mean()
                except Exception:
                    pass

        return df

    def _row_landmarks_to_dict(self, row: pd.Series) -> Dict[str, np.ndarray]:
        """Agrupa XY(Z) por ponto em um dicionário por frame."""
        pts = {}
        base_names = [
            'NOSE', 'LEFT_EAR', 'RIGHT_EAR',
            'LEFT_SHOULDER', 'RIGHT_SHOULDER',
            'LEFT_HIP', 'RIGHT_HIP',
            'LEFT_KNEE', 'RIGHT_KNEE',
            'LEFT_ANKLE', 'RIGHT_ANKLE'
        ]
        for name in base_names:
            x = row.get(f'{name}_x', np.nan)
            y = row.get(f'{name}_y', np.nan)
            z = row.get(f'{name}_z', 0.0)
            if not (np.isnan(x) or np.isnan(y)):
                pts[name] = np.array([float(x), float(y), float(z)], dtype=np.float64)
        return pts

    def add_angle_features(self, df: pd.DataFrame, exercise: str) -> pd.DataFrame:
        """Calcula ângulos por frame usando AdvancedAngleCalculator e adiciona ao DataFrame."""
        if df.empty:
            return df
        angles_knee = []
        angles_hip = []
        angles_torso = []
        angles_back = []
        knee_sym_diff = []
        for _, row in df.iterrows():
            lm = self._row_landmarks_to_dict(row)
            ang = self.angle_calculator.calculate_joint_angles_advanced(lm, exercise)
            angles_knee.append(float(ang.get('knee_angle', np.nan)))
            angles_hip.append(float(ang.get('hip_angle', np.nan)))
            angles_torso.append(float(ang.get('torso_angle', np.nan)))
            angles_back.append(float(ang.get('back_angle', np.nan)))
            knee_sym_diff.append(float(ang.get('knee_symmetry_diff', np.nan)))
        df = df.copy()
        df['knee_angle'] = angles_knee
        df['hip_angle'] = angles_hip
        df['torso_angle'] = angles_torso
        df['back_angle'] = angles_back
        df['knee_symmetry_diff'] = knee_sym_diff
        # Estabilidade unificada (compatível com interface)
        df['stability'] = df.get('torso_stability', 1.0)
        
        return df

    def _calculate_torso_stability(self, df: pd.DataFrame) -> pd.Series:
        """Calcula estabilidade do torso"""
        if 'LEFT_SHOULDER_y' in df.columns and 'RIGHT_SHOULDER_y' in df.columns:
            shoulder_variance = df[['LEFT_SHOULDER_y',
                                    'RIGHT_SHOULDER_y']].std(axis=1)
            return 1 / (1 + shoulder_variance)  # Inverso da variância
        return pd.Series(1.0, index=df.index)

    def _calculate_balance_index(self, df: pd.DataFrame) -> pd.Series:
        """Calcula índice de equilíbrio"""
        required = ['LEFT_HIP_x', 'RIGHT_HIP_x',
                    'LEFT_ANKLE_x', 'RIGHT_ANKLE_x']
        if all(col in df.columns for col in required):
            hip_center = (df['LEFT_HIP_x'] + df['RIGHT_HIP_x']) / 2
            ankle_center = (df['LEFT_ANKLE_x'] + df['RIGHT_ANKLE_x']) / 2
            balance = 1 - np.abs(hip_center - ankle_center)
            return np.clip(balance, 0, 1)
        return pd.Series(1.0, index=df.index)


def process_correct_movements(dataset_dir: str, output_dir: str) -> pd.DataFrame:

    video_exts = {'.mp4', '.avi', '.mov', '.mkv'}
    dataset_path = Path(dataset_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    parquet_file = output_path / 'correct_movements.parquet'

    extractor = OptimizedKeypointExtractor(max_workers=4)
    all_rows: List[pd.DataFrame] = []

    for video in dataset_path.rglob('*'):
        if video.suffix.lower() not in video_exts:
            continue
        try:
            cap = cv2.VideoCapture(str(video))
            if not cap.isOpened():
                print(f"Aviso: não foi possível abrir {video}")
                continue

            frames: List[np.ndarray] = []
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
            stride = max(fps // 3, 10)  # amostrar ~3x/segundo
            max_frames = 150
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
                continue

            landmarks_seq = extractor.extract_landmarks_batch(frames)
            if not landmarks_seq:
                continue

            df_feat = extractor.calculate_movement_features(landmarks_seq)
            exercise = video.parent.name.lower()
            if 'agachamento' in exercise or 'squat' in exercise:
                exercise = 'squat'
            elif 'terra' in exercise or 'deadlift' in exercise:
                exercise = 'deadlift'
            else:
                exercise = 'unknown'

            # Adiciona ângulos e estabilidade compatíveis com avaliação/modelo
            try:
                df_feat = extractor.add_angle_features(df_feat, exercise)
            except Exception as e:
                print(f"Aviso: falha ao calcular ângulos para {video}: {e}")

            # Validação leve: remove linhas sem ângulos essenciais
            essential_cols = ['knee_angle', 'hip_angle', 'torso_angle']
            try:
                df_feat = df_feat.dropna(subset=[c for c in essential_cols if c in df_feat.columns])
            except Exception:
                pass

            df_feat['exercise'] = exercise
            df_feat['label'] = 1  # corretos
            df_feat['video_file'] = str(video)
            df_feat['timestamp'] = np.arange(
                len(df_feat))  # índice temporal simples

            all_rows.append(df_feat)

        except Exception as e:
            print(f"Erro processando {video}: {e}")
            continue

    if all_rows:
        final_df = pd.concat(all_rows, ignore_index=True)
    else:
        final_df = pd.DataFrame()

    try:
        if not final_df.empty:
            final_df.to_parquet(parquet_file, engine='pyarrow')
            print(f"Parquet salvo em: {parquet_file}")
        else:
            print("Nenhum dado extraído. Parquet não será criado.")
    except Exception as e:
        print(f"Falha ao salvar parquet: {e}")

    return final_df
