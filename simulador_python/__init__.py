"""
Simulador físico e ferramentas de projeto do Rover Frugal 4WD/4WS.

Módulos:
    config              carrega o arquivo mestre de parâmetros e resolve derivados
    geometria_escada    marcha da roda de raios curvos sobre degraus (núcleo do projeto)
    csts                dimensionamento e dinâmica da suspensão torsional
    kinematics          cinemática 4WS e classificação de Siegwart
    terramechanics      cargas normais, estabilidade e comparação com skid-steer
    powertrain          motor, redutor, bateria, térmica e orçamento de energia
    multibody_dynamics  dinâmica no plano sagital com a carga a bordo
    benchmark           bateria de benchmarks e figuras
    relatorio           gerador do Relatório de Engenharia
"""

__version__ = "2.0.0"
__all__ = [
    "config", "geometria_escada", "csts", "kinematics", "terramechanics",
    "powertrain", "multibody_dynamics", "benchmark", "relatorio",
]
