# core/__init__.py
"""
Pacote core: mantenha imports leves no nível do pacote.

Evite importar submódulos pesados aqui para não causar falhas
em ambientes sem dependências nativas no momento da importação.
Importe submódulos diretamente onde forem usados, por exemplo:
    from core.angulos import AdvancedAngleCalculator
    from core.keypoints import OptimizedKeypointExtractor
    from core.scoring_system import EnhancedScoringSystem
    from core.analise import OneClassModelEvaluator, evaluate_oneclass_model
"""

__all__: list[str] = [
    # Exportações sugeridas; os módulos devem ser importados diretamente onde necessário.
]

