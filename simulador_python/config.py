"""
Configurações e Parâmetros Físicos do Rover Frugal 4WD/4WS
Fundamentado em:
- Siegwart & Nourbakhsh (2004) - Cinemática 4WS
- Wong (2022) - Terramecânica e Transferência de Carga
- Sclater & Chironis (2001) - Mecanismos de Acoplamento e Elásticos
- Jeong & Kim (2025) - Roda de 3 Raios Curvos e Suspensão C-STS
- Lei de Blondel (1675) & NBR 9050 - Escadarias Padrão
"""

import numpy as np

# ==========================================
# 1. PARÂMETROS MECÂNICOS DO CHASSI EM X
# ==========================================
MASS_TOTAL = 7.5          # Massa total com carga útil (kg)
MASS_PAYLOAD = 2.5        # Massa do notebook e suporte (kg)
MASS_CHASSIS = 5.0        # Massa do chassi em PVC, motores e rodas (kg)
GRAVITY = 9.80665         # Aceleração da gravidade (m/s²)
WEIGHT_TOTAL = MASS_TOTAL * GRAVITY # Peso total = ~73.55 N

# Dimensões da Base
WHEELBASE = 1.36          # Entre-eixos longitudinal L (m)
TRACK_WIDTH = 1.44        # Bitola transversal W (m)
LF = WHEELBASE / 2.0      # Distância do CG ao eixo dianteiro (m)
LR = WHEELBASE / 2.0      # Distância do CG ao eixo traseiro (m)

# Posições relativas das 4 rodas no referencial do robô (X: Lateral, Z: Longitudinal)
# Convenção: +X = Direita, -X = Esquerda, +Z = Ré, -Z = Frente
WHEEL_POSITIONS = {
    'FL': np.array([-TRACK_WIDTH / 2.0, 0.0, -WHEELBASE / 2.0]), # Dianteira Esquerda
    'FR': np.array([ TRACK_WIDTH / 2.0, 0.0, -WHEELBASE / 2.0]), # Dianteira Direita
    'RL': np.array([-TRACK_WIDTH / 2.0, 0.0,  WHEELBASE / 2.0]), # Traseira Esquerda
    'RR': np.array([ TRACK_WIDTH / 2.0, 0.0,  WHEELBASE / 2.0])  # Traseira Direita
}

# Centro de Gravidade e Efeito Pêndulo
H_CG_CHASSIS = 0.22       # Altura do CG do chassi acima do solo (m)
H_CG_PAYLOAD = 0.12       # Altura do CG da carga (fundo da caixa organizadora) (m)
H_CG_TOTAL = (MASS_CHASSIS * H_CG_CHASSIS + MASS_PAYLOAD * H_CG_PAYLOAD) / MASS_TOTAL # ~0.186 m
PENDULUM_ARM = 0.16       # Braço de alavanca do terço superior ao CG da carga (m)
PENDULUM_DAMPING = 4.5    # Amortecimento do balanço pendular (N·s/m)

# ==========================================
# 2. DIMENSIONAMENTO DA RODA (CÁLCULO DE BLONDEL)
# ==========================================
# Escada de Referência do Campus Parquetec (NBR 9050):
STAIR_RISER = 0.17        # Espelho do degrau E = 170 mm (m)
STAIR_TREAD = 0.30        # Piso do degrau P = 300 mm (m)
# Verificação de Blondel: 2*E + P = 2*(0.17) + 0.30 = 0.64 m (64 cm)
BLONDEL_VALUE = 2.0 * STAIR_RISER + STAIR_TREAD
STAIR_DIAGONAL = np.sqrt(STAIR_RISER**2 + STAIR_TREAD**2) # ~0.345 m (344.8 mm)

# Roda com 3 Raios Curvos (N = 3)
NUM_SPOKES = 3
SPOKE_ANGLE_STEP = 2.0 * np.pi / NUM_SPOKES # 120 graus (2.094 rad)
R_WHEEL_MAX = 0.150       # Raio máximo da ponta do raio = 150 mm (Diâmetro = 300 mm)
R_WHEEL_MIN = 0.045       # Raio do cubo C-STS = 45 mm (Diâmetro = 90 mm)
R_SPOKE_ARC = 0.135       # Raio de curvatura do arco espiral (m)

# ==========================================
# 3. SUSPENSÃO COMPLACENTE TORSIONAL (C-STS) - JEONG & KIM (2025)
# ==========================================
# Mola Espiral Plana em PLA/PETG: kt = (E * b * t^3) / (12 * L)
E_MODULUS_PLA = 3.5e9     # Módulo de Young do PLA (Pa)
CSTS_WIDTH_B = 0.015      # Largura axial da fita espiral b = 15 mm (m)
CSTS_THICKNESS_T = 0.005  # Espessura da lâmina t = 5 mm (m)
CSTS_LENGTH_L = 0.82728   # Comprimento desenrolado da espiral L = 827.28 mm (m)

# Rigidez Torsional Teórica e Empírica (Jeong & Kim, 2025)
KT_THEORETICAL = (E_MODULUS_PLA * CSTS_WIDTH_B * (CSTS_THICKNESS_T**3)) / (12.0 * CSTS_LENGTH_L) # ~0.661 N·m/rad
KT_EMPIRICAL = 0.547      # Rigidez empírica medida experimentalmente (N·m/rad)
CSTS_MAX_DEFLECTION = np.radians(35.0) # Deflexão angular máxima permitida (rad)

# Suspensão Linear por Elásticos de Escritório nas Mangas 4WS
K_RUBBER_BAND = 450.0     # Rigidez vertical do feixe de elásticos por roda (N/m)
C_RUBBER_BAND = 25.0      # Amortecimento histerético viscoso equivalente (N·s/m)
MAX_SUSP_TRAVEL = 0.035   # Curso máximo da suspensão linear = 35 mm (m)

# ==========================================
# 4. CINEMÁTICA E ATUADORES 4WD / 4WS
# ==========================================
MAX_LINEAR_SPEED = 1.2    # Velocidade linear máxima nominal (m/s)
MAX_STEER_ANGLE = np.radians(45.0) # Ângulo máximo de esterçamento das rodas (rad)
STEER_SLEW_RATE = np.radians(120.0) # Taxa máxima de esterçamento dos servos (rad/s)
MOTOR_TORQUE_MAX = 2.8    # Torque de stall por motorredutor 12V (N·m)
MOTOR_RATED_RPM = 120.0   # Rotação nominal sob carga (RPM)
COEFF_FRICTION_RUBBER = 0.85 # Coeficiente de atrito borracha-concreto
