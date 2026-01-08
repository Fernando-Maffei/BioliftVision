import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import os
import json
from enum import Enum
import json
import time


class ScoreLevel(Enum):
    """Níveis de qualidade do movimento"""
    EXCELENTE = "Excelente"
    MUITO_BOM = "Muito Bom"
    BOM = "Bom"
    REGULAR = "Regular"
    RUIM = "Ruim"
    MUITO_RUIM = "Muito Ruim"


@dataclass
class CriterionScore:
    """Pontuação individual de um critério"""
    name: str
    score: float
    max_score: float
    weight: float
    feedback: str
    details: Dict
    passed: bool


@dataclass
class DetailedEvaluation:
    """Avaliação detalhada do movimento"""
    total_score: float
    max_score: float
    percentage: float
    level: ScoreLevel
    criteria_scores: List[CriterionScore]
    overall_feedback: List[str]
    recommendations: List[str]
    ipf_lights: List[str]
    technical_details: Dict
    movement_quality_index: float


class EnhancedScoringSystem:
    """
    Sistema de pontuação aprimorado para análise de movimentos de powerlifting.
    Oferece feedback mais detalhado, critérios ponderados e análise progressiva.
    """
    
    def __init__(self, config_path: str = "config/scoring_config.json"):
        self.squat_criteria = {
            'depth': {
                'weight': 0.35,
                'max_score': 10,
                'thresholds': {
                    'excellent': 90,    # Profundidade excepcional
                    'very_good': 100,   # Profundidade IPF adequada
                    'good': 110,        # Profundidade aceitável
                    'regular': 123,     # Profundidade marginal (sensibilidade reduzida)
                    'poor': 133         # Profundidade insuficiente (sensibilidade reduzida)
                }
            },
            'stability': {
                'weight': 0.25,
                'max_score': 10,
                'thresholds': {
                    'excellent': 0.03,
                    'very_good': 0.05,
                    'good': 0.08,
                    'regular': 0.144,
                    'poor': 0.224
                }
            },
            'torso_position': {
                'weight': 0.20,
                'max_score': 10,
                'thresholds': {
                    'excellent': 5,
                    'very_good': 10,
                    'good': 15,
                    'regular': 23,
                    'poor': 33
                }
            },
            'lockout': {
                'weight': 0.15,
                'max_score': 10,
                'thresholds': {
                    'excellent': 178,
                    'very_good': 175,
                    'good': 170,
                    'regular': 163,
                    'poor': 158
                }
            },
            'symmetry': {
                'weight': 0.05,
                'max_score': 10,
                'thresholds': {
                    'excellent': 2,
                    'very_good': 5,
                    'good': 8,
                    'regular': 14,
                    'poor': 22
                }
            }
        }
        
        self.deadlift_criteria = {
            'lockout': {
                'weight': 0.40,  # Critério mais crítico
                'max_score': 10,
                'thresholds': {
                    'excellent': 178,
                    'very_good': 175,
                    'good': 170,
                    'regular': 163,
                    'poor': 158
                }
            },
            'back_position': {
                'weight': 0.30,
                'max_score': 10,
                'thresholds': {
                    'excellent': 10,
                    'very_good': 15,
                    'good': 20,
                    'regular': 28,
                    'poor': 38
                }
            },
            'bar_path': {
                'weight': 0.20,
                'max_score': 10,
                'thresholds': {
                    'excellent': 0.05,
                    'very_good': 0.08,
                    'good': 0.12,
                    'regular': 0.204,
                    'poor': 0.274
                }
            },
            'hip_extension': {
                'weight': 0.10,
                'max_score': 10,
                'thresholds': {
                    'excellent': 175,
                    'very_good': 170,
                    'good': 165,
                    'regular': 157,
                    'poor': 147
                }
            }
        }

        # Tenta carregar ajustes externos de configuração
        try:
            self._apply_external_config(config_path)
        except Exception:
            # Silencioso: em caso de falha, mantém defaults
            pass

    def _deep_update(self, target: dict, updates: dict):
        for k, v in updates.items():
            if isinstance(v, dict) and isinstance(target.get(k), dict):
                self._deep_update(target[k], v)
            else:
                target[k] = v
        return target

    def _apply_external_config(self, config_path: str):
        if not os.path.exists(config_path):
            return
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if 'squat' in cfg:
            self._deep_update(self.squat_criteria, cfg['squat'])
        if 'deadlift' in cfg:
            self._deep_update(self.deadlift_criteria, cfg['deadlift'])
    
    def _calculate_criterion_score(self, value: float, criterion: Dict, 
                                 higher_is_better: bool = True) -> Tuple[float, str, bool]:
        """
        Calcula a pontuação de um critério específico com base nos thresholds.
        
        Args:
            value: Valor medido
            criterion: Configuração do critério
            higher_is_better: Se valores maiores são melhores
            
        Returns:
            Tuple com (pontuação, nível, passou)
        """
        thresholds = criterion['thresholds']
        max_score = criterion['max_score']
        
        if higher_is_better:
            if value >= thresholds['excellent']:
                return max_score, 'excellent', True
            elif value >= thresholds['very_good']:
                return max_score * 0.9, 'very_good', True
            elif value >= thresholds['good']:
                return max_score * 0.75, 'good', True
            elif value >= thresholds['regular']:
                return max_score * 0.5, 'regular', False
            else:
                return max_score * 0.2, 'poor', False
        else:
            if value <= thresholds['excellent']:
                return max_score, 'excellent', True
            elif value <= thresholds['very_good']:
                return max_score * 0.9, 'very_good', True
            elif value <= thresholds['good']:
                return max_score * 0.75, 'good', True
            elif value <= thresholds['regular']:
                return max_score * 0.5, 'regular', False
            else:
                return max_score * 0.2, 'poor', False
    
    def _generate_feedback(self, criterion_name: str, level: str, value: float, 
                          exercise: str) -> str:
        """Gera feedback específico para cada critério"""
        feedback_templates = {
            'squat': {
                'depth': {
                    'excellent': f"🏆 Profundidade excepcional! Ângulo: {value:.1f}° - Muito abaixo do paralelo",
                    'very_good': f"✅ Profundidade IPF perfeita! Ângulo: {value:.1f}° - Quadril abaixo do joelho",
                    'good': f"✅ Profundidade adequada. Ângulo: {value:.1f}° - Dentro dos padrões",
                    'regular': f"⚠️ Profundidade marginal. Ângulo: {value:.1f}° - Próximo do limite",
                    'poor': f"❌ Profundidade insuficiente! Ângulo: {value:.1f}° - Desça mais"
                },
                'stability': {
                    'excellent': f"🏆 Movimento extremamente estável! Variação: {value:.3f}",
                    'very_good': f"✅ Excelente controle do movimento. Variação: {value:.3f}",
                    'good': f"✅ Movimento controlado. Variação: {value:.3f}",
                    'regular': f"⚠️ Movimento um pouco instável. Variação: {value:.3f}",
                    'poor': f"❌ Movimento muito instável! Variação: {value:.3f} - Trabalhe o core"
                },
                'torso_position': {
                    'excellent': f"🏆 Torso perfeitamente ereto! Inclinação: {value:.1f}°",
                    'very_good': f"✅ Excelente postura do torso. Inclinação: {value:.1f}°",
                    'good': f"✅ Boa postura do torso. Inclinação: {value:.1f}°",
                    'regular': f"⚠️ Torso ligeiramente inclinado. Inclinação: {value:.1f}°",
                    'poor': f"❌ Torso muito inclinado! Inclinação: {value:.1f}° - Mantenha o peito alto"
                },
                'lockout': {
                    'excellent': f"🏆 Extensão completa perfeita! Ângulo: {value:.1f}°",
                    'very_good': f"✅ Excelente extensão dos joelhos. Ângulo: {value:.1f}°",
                    'good': f"✅ Boa extensão. Ângulo: {value:.1f}°",
                    'regular': f"⚠️ Extensão incompleta. Ângulo: {value:.1f}°",
                    'poor': f"❌ Extensão muito incompleta! Ângulo: {value:.1f}° - Estenda completamente"
                }
            },
            'deadlift': {
                'lockout': {
                    'excellent': f"🏆 Lockout perfeito! Ângulo: {value:.1f}° - Ombros para trás",
                    'very_good': f"✅ Excelente lockout. Ângulo: {value:.1f}°",
                    'good': f"✅ Bom lockout. Ângulo: {value:.1f}°",
                    'regular': f"⚠️ Lockout incompleto. Ângulo: {value:.1f}°",
                    'poor': f"❌ Lockout muito incompleto! Ângulo: {value:.1f}° - Finalize o movimento"
                },
                'back_position': {
                    'excellent': f"🏆 Coluna perfeitamente neutra! Ângulo: {value:.1f}°",
                    'very_good': f"✅ Excelente posição das costas. Ângulo: {value:.1f}°",
                    'good': f"✅ Boa posição das costas. Ângulo: {value:.1f}°",
                    'regular': f"⚠️ Costas ligeiramente arqueadas. Ângulo: {value:.1f}°",
                    'poor': f"❌ Costas muito arqueadas! Ângulo: {value:.1f}° - Risco de lesão"
                },
                'bar_path': {
                    'excellent': f"🏆 Trajetória da barra perfeita! Desvio: {value:.3f}",
                    'very_good': f"✅ Excelente trajetória. Desvio: {value:.3f}",
                    'good': f"✅ Boa trajetória. Desvio: {value:.3f}",
                    'regular': f"⚠️ Trajetória irregular. Desvio: {value:.3f}",
                    'poor': f"❌ Trajetória muito irregular! Desvio: {value:.3f} - Mantenha próximo ao corpo"
                }
            }
        }
        
        return feedback_templates.get(exercise, {}).get(criterion_name, {}).get(level, 
                                                                               f"Critério {criterion_name}: {value}")
    
    def _generate_recommendations(self, criteria_scores: List[CriterionScore], 
                                exercise: str) -> List[str]:
        """Gera recomendações específicas baseadas nos pontos fracos"""
        recommendations = []
        
        # Identifica os critérios com pior desempenho
        weak_criteria = [c for c in criteria_scores if not c.passed]
        weak_criteria.sort(key=lambda x: x.score / x.max_score)
        
        recommendation_map = {
            'squat': {
                'depth': [
                    "🎯 Trabalhe mobilidade de tornozelo e quadril",
                    "🎯 Pratique agachamentos com caixa para referência de profundidade",
                    "🎯 Fortaleça glúteos e posteriores de coxa"
                ],
                'stability': [
                    "🎯 Fortaleça músculos do core (prancha, dead bug)",
                    "🎯 Pratique agachamentos unilaterais",
                    "🎯 Trabalhe propriocepção com superfícies instáveis"
                ],
                'torso_position': [
                    "🎯 Fortaleça músculos das costas (remadas, pull-ups)",
                    "🎯 Trabalhe mobilidade torácica",
                    "🎯 Pratique postura com bastão nas costas"
                ]
            },
            'deadlift': {
                'lockout': [
                    "🎯 Fortaleça glúteos com hip thrusts",
                    "🎯 Pratique lockouts parciais",
                    "🎯 Trabalhe extensão de quadril"
                ],
                'back_position': [
                    "🎯 Fortaleça músculos das costas",
                    "🎯 Trabalhe mobilidade de quadril",
                    "🎯 Pratique posição inicial correta"
                ],
                'bar_path': [
                    "🎯 Pratique com barra vazia focando na trajetória",
                    "🎯 Mantenha a barra próxima ao corpo",
                    "🎯 Trabalhe coordenação quadril-joelho"
                ]
            }
        }
        
        for criterion in weak_criteria[:2]:  # Top 2 pontos fracos
            recs = recommendation_map.get(exercise, {}).get(criterion.name, [])
            recommendations.extend(recs[:2])  # Máximo 2 recomendações por critério
        
        return recommendations
    
    def _calculate_movement_quality_index(self, criteria_scores: List[CriterionScore]) -> float:
        """
        Calcula um índice de qualidade do movimento (0-100) considerando:
        - Consistência entre critérios
        - Pontuação ponderada
        - Penalização por critérios críticos falhados
        """
        if not criteria_scores:
            return 0.0
        
        # Pontuação ponderada base
        weighted_score = sum(c.score * c.weight for c in criteria_scores)
        max_weighted_score = sum(c.max_score * c.weight for c in criteria_scores)
        base_score = (weighted_score / max_weighted_score) * 100
        
        # Penalização por inconsistência
        scores_normalized = [c.score / c.max_score for c in criteria_scores]
        consistency_penalty = np.std(scores_normalized) * 10
        
        # Penalização por critérios críticos falhados
        critical_penalty = 0
        for criterion in criteria_scores:
            if criterion.weight > 0.3 and not criterion.passed:  # Critério crítico
                critical_penalty += 15
        
        final_score = max(0, base_score - consistency_penalty - critical_penalty)
        return min(100, final_score)
    
    def _determine_score_level(self, percentage: float) -> ScoreLevel:
        """Determina o nível de qualidade baseado na porcentagem"""
        if percentage >= 90:
            return ScoreLevel.EXCELENTE
        elif percentage >= 80:
            return ScoreLevel.MUITO_BOM
        elif percentage >= 70:
            return ScoreLevel.BOM
        elif percentage >= 60:
            return ScoreLevel.REGULAR
        elif percentage >= 40:
            return ScoreLevel.RUIM
        else:
            return ScoreLevel.MUITO_RUIM
    
    def _get_ipf_lights(self, criteria_scores: List[CriterionScore], exercise: str) -> List[str]:
        """Simula as luzes dos juízes IPF baseado nos critérios críticos"""
        critical_criteria = [c for c in criteria_scores if c.weight > 0.25]
        passed_critical = sum(1 for c in critical_criteria if c.passed)
        total_critical = len(critical_criteria)
        
        if total_critical == 0:
            # Sem critérios críticos avaliados: não pode receber 3 brancas
            return ['red', 'red', 'red']
        elif passed_critical == total_critical:
            return ['white', 'white', 'white']  # 3 luzes brancas
        elif passed_critical >= total_critical * 0.67:
            return ['white', 'white', 'red']    # 2 luzes brancas
        elif passed_critical >= total_critical * 0.33:
            return ['white', 'red', 'red']      # 1 luz branca
        else:
            return ['red', 'red', 'red']        # 3 luzes vermelhas
    
    def evaluate_squat(self, angles: Dict[str, float], stability: float) -> DetailedEvaluation:
        """Avalia agachamento com sistema aprimorado"""
        if not angles:
            return self._create_empty_evaluation("Dados insuficientes para análise")
        
        criteria_scores = []
        
        # Avalia cada critério
        knee_angle = angles.get('knee_angle', 180)
        score, level, passed = self._calculate_criterion_score(
            knee_angle, self.squat_criteria['depth'], higher_is_better=False
        )
        criteria_scores.append(CriterionScore(
            name='depth',
            score=score,
            max_score=self.squat_criteria['depth']['max_score'],
            weight=self.squat_criteria['depth']['weight'],
            feedback=self._generate_feedback('depth', level, knee_angle, 'squat'),
            details={'angle': knee_angle, 'threshold_passed': passed},
            passed=passed
        ))
        
        # Estabilidade
        score, level, passed = self._calculate_criterion_score(
            stability, self.squat_criteria['stability'], higher_is_better=False
        )
        criteria_scores.append(CriterionScore(
            name='stability',
            score=score,
            max_score=self.squat_criteria['stability']['max_score'],
            weight=self.squat_criteria['stability']['weight'],
            feedback=self._generate_feedback('stability', level, stability, 'squat'),
            details={'stability_value': stability, 'threshold_passed': passed},
            passed=passed
        ))
        
        # Posição do torso
        torso_angle = angles.get('torso_angle', 0)
        score, level, passed = self._calculate_criterion_score(
            torso_angle, self.squat_criteria['torso_position'], higher_is_better=False
        )
        criteria_scores.append(CriterionScore(
            name='torso_position',
            score=score,
            max_score=self.squat_criteria['torso_position']['max_score'],
            weight=self.squat_criteria['torso_position']['weight'],
            feedback=self._generate_feedback('torso_position', level, torso_angle, 'squat'),
            details={'angle': torso_angle, 'threshold_passed': passed},
            passed=passed
        ))

        # Simetria (se disponível)
        symmetry_value = None
        if 'knee_symmetry' in angles:
            symmetry_value = angles.get('knee_symmetry')
        elif 'knee_symmetry_diff' in angles:
            symmetry_value = angles.get('knee_symmetry_diff')
        if symmetry_value is not None:
            score, level, passed = self._calculate_criterion_score(
                float(symmetry_value), self.squat_criteria['symmetry'], higher_is_better=False
            )
            criteria_scores.append(CriterionScore(
                name='symmetry',
                score=score,
                max_score=self.squat_criteria['symmetry']['max_score'],
                weight=self.squat_criteria['symmetry']['weight'],
                feedback=self._generate_feedback('symmetry', level, float(symmetry_value), 'squat'),
                details={'symmetry_value': float(symmetry_value), 'threshold_passed': passed},
                passed=passed
            ))

        # Lockout: usa lockout_angle se disponível; caso contrário, avalia lockout
        # apenas quando o joelho está próximo da extensão (fase topo)
        lockout_angle_src = None
        if 'lockout_angle' in angles:
            lockout_angle_src = float(angles.get('lockout_angle'))
        else:
            # fallback: somente considera lockout no topo
            if knee_angle is not None and float(knee_angle) >= 165.0:
                lockout_angle_src = float(knee_angle)
        if lockout_angle_src is not None:
            score, level, passed = self._calculate_criterion_score(
                lockout_angle_src, self.squat_criteria['lockout'], higher_is_better=True
            )
            criteria_scores.append(CriterionScore(
                name='lockout',
                score=score,
                max_score=self.squat_criteria['lockout']['max_score'],
                weight=self.squat_criteria['lockout']['weight'],
                feedback=self._generate_feedback('lockout', level, lockout_angle_src, 'squat'),
                details={'angle': lockout_angle_src, 'threshold_passed': passed},
                passed=passed
            ))
        
        return self._compile_evaluation(criteria_scores, 'squat')
    
    def evaluate_deadlift(self, angles: Dict[str, float], stability: float) -> DetailedEvaluation:
        """Avalia levantamento terra com sistema aprimorado"""
        if not angles:
            return self._create_empty_evaluation("Dados insuficientes para análise")
        
        criteria_scores = []
        
        # Fase do movimento: só avalia lockout/hip/back_position quando próximo ao topo
        knee_angle = angles.get('knee_angle', 0)
        in_lockout_phase = knee_angle is not None and float(knee_angle) >= 165.0

        # Lockout: avalia normal no topo; fora do topo marca como incompleto
        if in_lockout_phase:
            score, level, passed = self._calculate_criterion_score(
                knee_angle, self.deadlift_criteria['lockout'], higher_is_better=True
            )
        else:
            score = self.deadlift_criteria['lockout']['max_score'] * 0.2
            level = 'poor'
            passed = False
        criteria_scores.append(CriterionScore(
            name='lockout',
            score=score,
            max_score=self.deadlift_criteria['lockout']['max_score'],
            weight=self.deadlift_criteria['lockout']['weight'],
            feedback=self._generate_feedback('lockout', level, knee_angle, 'deadlift'),
            details={'angle': knee_angle, 'threshold_passed': passed},
            passed=passed
        ))

        # Posição das costas: normal no topo; fora do topo limita a pontuação a 'regular'
        back_angle = angles.get('back_angle', 0)
        if in_lockout_phase:
            score, level, passed = self._calculate_criterion_score(
                back_angle, self.deadlift_criteria['back_position'], higher_is_better=False
            )
        else:
            # Fora do lockout, evita 'Excelente' por postura naturalmente inclinada
            base_score, base_level, base_passed = self._calculate_criterion_score(
                back_angle, self.deadlift_criteria['back_position'], higher_is_better=False
            )
            # Cap no máximo como 'regular' e não passa critério
            score = self.deadlift_criteria['back_position']['max_score'] * 0.5
            level = 'regular'
            passed = False
        criteria_scores.append(CriterionScore(
            name='back_position',
            score=score,
            max_score=self.deadlift_criteria['back_position']['max_score'],
            weight=self.deadlift_criteria['back_position']['weight'],
            feedback=self._generate_feedback('back_position', level, back_angle, 'deadlift'),
            details={'angle': back_angle, 'threshold_passed': passed},
            passed=passed
        ))
        
        # Trajetória da barra
        score, level, passed = self._calculate_criterion_score(
            stability, self.deadlift_criteria['bar_path'], higher_is_better=False
        )
        criteria_scores.append(CriterionScore(
            name='bar_path',
            score=score,
            max_score=self.deadlift_criteria['bar_path']['max_score'],
            weight=self.deadlift_criteria['bar_path']['weight'],
            feedback=self._generate_feedback('bar_path', level, stability, 'deadlift'),
            details={'stability_value': stability, 'threshold_passed': passed},
            passed=passed
        ))
        
        # Extensão do quadril: normal no topo; fora do topo marca como incompleta
        hip_angle = angles.get('hip_angle', 0)
        if in_lockout_phase:
            score, level, passed = self._calculate_criterion_score(
                hip_angle, self.deadlift_criteria['hip_extension'], higher_is_better=True
            )
        else:
            score = self.deadlift_criteria['hip_extension']['max_score'] * 0.2
            level = 'poor'
            passed = False
        criteria_scores.append(CriterionScore(
            name='hip_extension',
            score=score,
            max_score=self.deadlift_criteria['hip_extension']['max_score'],
            weight=self.deadlift_criteria['hip_extension']['weight'],
            feedback=self._generate_feedback('hip_extension', level, hip_angle, 'deadlift'),
            details={'angle': hip_angle, 'threshold_passed': passed},
            passed=passed
        ))
        
        return self._compile_evaluation(criteria_scores, 'deadlift')
    
    def _compile_evaluation(self, criteria_scores: List[CriterionScore], exercise: str) -> DetailedEvaluation:
        """Compila a avaliação final"""
        total_score = sum(c.score * c.weight for c in criteria_scores)
        max_score = sum(c.max_score * c.weight for c in criteria_scores)
        percentage = (total_score / max_score) * 100 if max_score > 0 else 0
        
        level = self._determine_score_level(percentage)
        recommendations = self._generate_recommendations(criteria_scores, exercise)
        ipf_lights = self._get_ipf_lights(criteria_scores, exercise)
        movement_quality_index = self._calculate_movement_quality_index(criteria_scores)
        
        # Feedback geral
        overall_feedback = []
        passed_criteria = sum(1 for c in criteria_scores if c.passed)
        total_criteria = len(criteria_scores)
        
        if passed_criteria == total_criteria:
            overall_feedback.append("🏆 Movimento tecnicamente excelente!")
        elif passed_criteria >= total_criteria * 0.75:
            overall_feedback.append("✅ Bom movimento com pequenos ajustes necessários")
        elif passed_criteria >= total_criteria * 0.5:
            overall_feedback.append("⚠️ Movimento aceitável, mas precisa de melhorias")
        else:
            overall_feedback.append("❌ Movimento precisa de correções significativas")
        
        overall_feedback.append(f"📊 Índice de Qualidade: {movement_quality_index:.1f}/100")
        
        return DetailedEvaluation(
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            level=level,
            criteria_scores=criteria_scores,
            overall_feedback=overall_feedback,
            recommendations=recommendations,
            ipf_lights=ipf_lights,
            technical_details={
                'exercise': exercise,
                'criteria_count': len(criteria_scores),
                'passed_criteria': passed_criteria,
                'movement_quality_index': movement_quality_index
            },
            movement_quality_index=movement_quality_index
        )
    
    def _create_empty_evaluation(self, reason: str) -> DetailedEvaluation:
        """Cria uma avaliação vazia para casos de erro"""
        return DetailedEvaluation(
            total_score=0,
            max_score=10,
            percentage=0,
            level=ScoreLevel.MUITO_RUIM,
            criteria_scores=[],
            overall_feedback=[f"❌ {reason}"],
            recommendations=["🎯 Verifique a captura de movimento e tente novamente"],
            ipf_lights=['red', 'red', 'red'],
            technical_details={'error': reason},
            movement_quality_index=0
        )
    
def export_evaluation_report(self, evaluation: DetailedEvaluation, 
                               filename: str = None) -> str:
        """Exporta relatório detalhado da avaliação"""
        if filename is None:
            filename = f"evaluation_report_{int(time.time())}.json"
        
        report = {
            'summary': {
                'total_score': evaluation.total_score,
                'max_score': evaluation.max_score,
                'percentage': evaluation.percentage,
                'level': evaluation.level.value,
                'movement_quality_index': evaluation.movement_quality_index
            },
            'criteria_breakdown': [
                {
                    'name': c.name,
                    'score': c.score,
                    'max_score': c.max_score,
                    'weight': c.weight,
                    'passed': c.passed,
                    'feedback': c.feedback,
                    'details': c.details
                }
                for c in evaluation.criteria_scores
            ],
            'feedback': {
                'overall': evaluation.overall_feedback,
                'recommendations': evaluation.recommendations,
                'ipf_lights': evaluation.ipf_lights
            },
            'technical_details': evaluation.technical_details
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filename

# --------------------------
# API Pública de Regras IPF
# --------------------------
def _convert_detailed_to_basic_dict(evaluation: DetailedEvaluation) -> Dict:
    """Converte DetailedEvaluation para um dicionário simples para consumo do pipeline/UI."""
    try:
        lights = list(getattr(evaluation, 'ipf_lights', []) or [])
        valid = lights.count('white') >= 2
        return {
            'valid': valid,
            'score': float(getattr(evaluation, 'total_score', 0.0)),
            'max_score': float(getattr(evaluation, 'max_score', 0.0)),
            'lights': lights,
            'feedback': list(getattr(evaluation, 'overall_feedback', []) or []),
            'quality': float(getattr(evaluation, 'movement_quality_index', 0.0))
        }
    except Exception:
        return {'valid': False, 'score': 0.0, 'max_score': 0.0, 'lights': ['red','red','red'], 'feedback': [], 'quality': 0.0}


def apply_ipf_rules(dataset, lift_type: Optional[str] = None):
    """
    Aplica regras IPF nos dados fornecidos e retorna uma lista de resultados.
    - `dataset` pode ser um pandas.DataFrame, lista de dicts ou um único dict
    - `lift_type` pode ser 'squat' ou 'deadlift' (opcional se o dataset tiver coluna 'exercise')
    O resultado de cada item inclui: valid, score, max_score, lights, feedback, quality.
    """
    try:
        try:
            import pandas as pd  # type: ignore
        except Exception:
            pd = None

        scorer = EnhancedScoringSystem()

        def evaluate_row(row) -> Dict:
            exercise = (row.get('exercise') or lift_type or 'squat').lower()
            angles = row.get('angles') or {
                'knee_angle': float(row.get('knee_angle', 170)),
                'hip_angle': float(row.get('hip_angle', 170)),
                'torso_angle': float(row.get('torso_angle', 10)),
                'back_angle': float(row.get('back_angle', 15)),
            }
            stability = float(row.get('stability', row.get('bar_path_deviation', 0.08)))
            if exercise.startswith('squat'):
                ev = scorer.evaluate_squat(angles, stability)
            else:
                ev = scorer.evaluate_deadlift(angles, stability)
            return _convert_detailed_to_basic_dict(ev)

        results: List[Dict] = []
        if pd is not None and hasattr(dataset, 'iloc'):
            # pandas DataFrame
            for _, r in dataset.iterrows():
                results.append(evaluate_row(r.to_dict()))
        elif isinstance(dataset, list):
            for r in dataset:
                results.append(evaluate_row(r))
        elif isinstance(dataset, dict):
            results.append(evaluate_row(dataset))
        else:
            # tipo desconhecido
            results.append(evaluate_row({}))
        return results
    except Exception:
        return []


def score_movements(dataset, lift_type: Optional[str] = None):
    """Alias para apply_ipf_rules que enfatiza pontuação agregada dos movimentos."""
    return apply_ipf_rules(dataset, lift_type)


def validate_movements(dataset, lift_type: Optional[str] = None):
    """
    Valida movimentos contra regras IPF e retorna apenas sinalizadores de validade
    e luzes por item.
    """
    try:
        results = apply_ipf_rules(dataset, lift_type)
        return [{'valid': r.get('valid', False), 'lights': r.get('lights', [])} for r in results]
    except Exception:
        return []
