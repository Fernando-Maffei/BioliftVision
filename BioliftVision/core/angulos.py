import numpy as np
from typing import Dict, List, Tuple
from scipy.spatial.transform import Rotation as R

class AdvancedAngleCalculator:
    """
    Calculadora avançada de ângulos com análise 3D robusta
    """
    
    def __init__(self):
        # Mantém nomes originais para preservar lado (LEFT/RIGHT)
        # Evita perdas de informação e inconsistências com chamadas existentes
        self.landmark_mapping = None
    
    def calculate_3d_angle_robust(self, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        try:
            a = self._ensure_3d(a)
            b = self._ensure_3d(b)
            c = self._ensure_3d(c)
            
            if np.any(np.isnan([a, b, c])) or np.all(a == b) or np.all(b == c):
                return 0.0
            
            ba = a - b
            bc = c - b
            
            ba_norm = np.linalg.norm(ba)
            bc_norm = np.linalg.norm(bc)
            
            if ba_norm < 1e-10 or bc_norm < 1e-10:
                return 0.0
            
            cos_angle = np.dot(ba, bc) / (ba_norm * bc_norm)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            
            return np.degrees(np.arccos(cos_angle))
            
        except Exception:
            return 0.0
    
    def calculate_joint_angles_advanced(self, landmarks: Dict, exercise: str) -> Dict:
        """Calcula ângulos articulares avançados"""
        angles = {}
        # Usa landmarks conforme fornecidos, preservando lado
        
        try:
            if exercise.lower() in ['squat', 'agachamento']:
                angles.update(self._squat_angles_advanced(landmarks))
            elif exercise.lower() in ['deadlift', 'terra']:
                angles.update(self._deadlift_angles_advanced(landmarks))
            
            # Ângulos de simetria
            angles.update(self._symmetry_angles(landmarks))
            
        except Exception as e:
            print(f"Erro no cálculo de ângulos: {e}")
        
        return angles
    
    def _squat_angles_advanced(self, landmarks: Dict) -> Dict:
        """Ângulos avançados para agachamento"""
        angles = {}
        
        # Ângulo do joelho (média entre esquerdo e direito)
        knee_angles = []
        for side in ['LEFT', 'RIGHT']:
            if all(k in landmarks for k in [f"{side}_ANKLE", f"{side}_KNEE", f"{side}_HIP"]):
                angle = self.calculate_3d_angle_robust(
                    landmarks[f"{side}_ANKLE"], 
                    landmarks[f"{side}_KNEE"], 
                    landmarks[f"{side}_HIP"]
                )
                knee_angles.append(angle)
        
        if knee_angles:
            angles['knee_angle'] = np.mean(knee_angles)
            angles['knee_symmetry'] = np.std(knee_angles) if len(knee_angles) > 1 else 0
        
        # Ângulo do quadril
        if all(k in landmarks for k in ['LEFT_KNEE', 'LEFT_HIP', 'LEFT_SHOULDER']):
            angles['hip_angle'] = self.calculate_3d_angle_robust(
                landmarks['LEFT_KNEE'], landmarks['LEFT_HIP'], landmarks['LEFT_SHOULDER']
            )
        
        # Inclinação do torso
        if all(k in landmarks for k in ['LEFT_HIP', 'LEFT_SHOULDER']):
            # Ajuste do eixo vertical para coordenadas de imagem (y cresce para baixo)
            vertical = np.array([0, -1, 0])  # Vetor vertical para cima
            shoulder = self._ensure_3d(landmarks['LEFT_SHOULDER'])
            hip = self._ensure_3d(landmarks['LEFT_HIP'])
            torso_vector = shoulder - hip
            torso_vector_norm = torso_vector / np.linalg.norm(torso_vector)

            angles['torso_angle'] = np.degrees(np.arccos(
                np.clip(np.dot(torso_vector_norm, vertical), -1.0, 1.0)
            ))
        
        return angles
    
    def _deadlift_angles_advanced(self, landmarks: Dict) -> Dict:
        """Ângulos avançados para levantamento terra"""
        angles = {}
        
        # Ângulo do joelho (média entre esquerdo e direito)
        knee_angles = []
        for side in ['LEFT', 'RIGHT']:
            if all(k in landmarks for k in [f"{side}_ANKLE", f"{side}_KNEE", f"{side}_HIP"]):
                angle = self.calculate_3d_angle_robust(
                    landmarks[f"{side}_ANKLE"],
                    landmarks[f"{side}_KNEE"],
                    landmarks[f"{side}_HIP"]
                )
                knee_angles.append(angle)
        if knee_angles:
            angles['knee_angle'] = np.mean(knee_angles)
            angles['knee_symmetry'] = np.std(knee_angles) if len(knee_angles) > 1 else 0

        # Extensão do quadril (ângulo no quadril: joelho-quadril-ombro)
        if all(k in landmarks for k in ['LEFT_KNEE', 'LEFT_HIP', 'LEFT_SHOULDER']):
            angles['hip_angle'] = self.calculate_3d_angle_robust(
                landmarks['LEFT_KNEE'], landmarks['LEFT_HIP'], landmarks['LEFT_SHOULDER']
            )

        # Ângulo das costas: inclinação do vetor torso (quadril->ombro) em relação ao vertical
        if all(k in landmarks for k in ['LEFT_HIP', 'LEFT_SHOULDER']):
            vertical = np.array([0, -1, 0])  # eixo vertical para cima (imagem y cresce para baixo)
            shoulder = self._ensure_3d(landmarks['LEFT_SHOULDER'])
            hip = self._ensure_3d(landmarks['LEFT_HIP'])
            torso_vector = shoulder - hip
            norm = np.linalg.norm(torso_vector)
            if norm > 1e-10:
                torso_vector_norm = torso_vector / norm
                angles['back_angle'] = np.degrees(np.arccos(
                    np.clip(np.dot(torso_vector_norm, vertical), -1.0, 1.0)
                ))
            else:
                angles['back_angle'] = 0.0
        
        # Ângulo de lockout
        if all(k in landmarks for k in ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE']):
            angles['lockout_angle'] = self.calculate_3d_angle_robust(
                landmarks['LEFT_HIP'], landmarks['LEFT_KNEE'], landmarks['LEFT_ANKLE']
            )
        
        return angles
    
    def _symmetry_angles(self, landmarks: Dict) -> Dict:
        """Calcula ângulos de simetria bilateral"""
        symmetry = {}
        
        # Simetria joelho
        left_knee = self.calculate_3d_angle_robust(
            landmarks.get('LEFT_ANKLE', (0,0,0)),
            landmarks.get('LEFT_KNEE', (0,0,0)),
            landmarks.get('LEFT_HIP', (0,0,0))
        )
        right_knee = self.calculate_3d_angle_robust(
            landmarks.get('RIGHT_ANKLE', (0,0,0)),
            landmarks.get('RIGHT_KNEE', (0,0,0)),
            landmarks.get('RIGHT_HIP', (0,0,0))
        )
        
        if left_knee > 0 and right_knee > 0:
            symmetry['knee_symmetry_diff'] = abs(left_knee - right_knee)
        
        return symmetry
    
    def _ensure_3d(self, point) -> np.ndarray:
        """Garante coordenadas 3D"""
        if len(point) == 2:
            return np.array([point[0], point[1], 0.0])
        return np.array(point[:3])
    
    def _map_landmarks(self, landmarks: Dict) -> Dict:
        """Compatibilidade legado: retorna landmarks sem alterar nomes.
        Mantemos chaves como 'LEFT_HIP', 'RIGHT_KNEE', etc.
        """
        return dict(landmarks)