"""
Mecânica da Roda de 3 Raios Curvos e Suspensão Torsional Espiral (C-STS)
Baseado em: Jeong & Kim (2025) - Appl. Sci. 2025, 15, 5985
"""

import numpy as np
from .config import (
    R_WHEEL_MAX, R_WHEEL_MIN, NUM_SPOKES, SPOKE_ANGLE_STEP,
    KT_EMPIRICAL, KT_THEORETICAL, CSTS_MAX_DEFLECTION,
    E_MODULUS_PLA, CSTS_WIDTH_B, CSTS_THICKNESS_T, CSTS_LENGTH_L
)

class CurvedSpokeCSTSWheel:
    def __init__(self, with_csts: bool = True):
        self.with_csts = with_csts
        self.num_spokes = NUM_SPOKES
        self.r_max = R_WHEEL_MAX  # 0.150 m (150 mm)
        self.r_min = R_WHEEL_MIN  # 0.045 m (45 mm)
        self.kt = KT_EMPIRICAL if with_csts else 1e5 # Rigidez (N·m/rad) - 1e5 = Rígido
        self.torsional_deflection = 0.0 # Delta theta (rad)
        self.wheel_angle = 0.0          # Ângulo acumulado de giro da roda (rad)
        self.phase = 'CCS'              # 'CCS' (Continuous Contact) ou 'DCS' (Discontinuous Transition)
        self.current_effective_radius = self.r_min
        self.stored_energy = 0.0        # Energia elástica U = 0.5 * kt * Delta_theta^2 (Joules)
        self.deceleration_spike = 0.0   # Aceleração/desaceleração no ponto de contato (m/s²)

    def update_wheel_contact(self, motor_angular_speed: float, dt: float):
        """
        Atualiza o estado de contato da roda e a resposta da suspensão C-STS conforme Jeong & Kim (2025).
        """
        # Ângulo dentro do setor de 120° (2*pi/3) de cada raio
        spoke_phase_angle = np.fmod(self.wheel_angle, SPOKE_ANGLE_STEP)
        t_spoke = spoke_phase_angle / SPOKE_ANGLE_STEP # Fração de 0 a 1

        # 1. Raio Efetivo de Curvatura r(t)
        if t_spoke < 0.92:
            # Fase CCS (Continuous Contact State): raio cresce monotonicamente de r_min a r_max
            self.phase = 'CCS'
            self.current_effective_radius = self.r_min + (self.r_max - self.r_min) * (t_spoke / 0.92)**0.85

            if self.with_csts:
                # Na fase CCS, o motor deflete a mola C-STS acumulando energia elástica
                target_deflection = (motor_angular_speed / 5.0) * np.sin(t_spoke * np.pi) * 0.15
                self.torsional_deflection += (target_deflection - self.torsional_deflection) * (dt * 15.0)
            else:
                self.torsional_deflection = 0.0

            self.deceleration_spike = 0.0

        else:
            # Fase DCS (Discontinuous Contact State): transição do raio da ponta para a raiz do próximo
            self.phase = 'DCS'
            # Queda brusca teórica: Delta_v = omega * (r_max - r_min)
            delta_v_theoretical = motor_angular_speed * (self.r_max - self.r_min)
            dt_dcs = max(1e-3, dt * 2.0)

            if self.with_csts:
                # O C-STS libera a energia armazenada e absorve o choque por deflexão reversa
                # Reduz o pico de desaceleração em > 40%
                self.torsional_deflection -= self.torsional_deflection * (dt * 20.0)
                self.deceleration_spike = (delta_v_theoretical / dt_dcs) * 0.45 # Amortecido
                self.current_effective_radius = self.r_min + (self.r_max - self.r_min) * 0.1
            else:
                # Roda rígida sem suspensão: desaceleração total instantânea violenta
                self.torsional_deflection = 0.0
                self.deceleration_spike = delta_v_theoretical / dt_dcs # Choque bruto
                self.current_effective_radius = self.r_min

        # Atualizar rotação física da roda
        effective_angular_speed = motor_angular_speed + (self.torsional_deflection * 5.0 if self.with_csts else 0.0)
        self.wheel_angle += effective_angular_speed * dt

        # Energia potencial elástica armazenada na mola espiral C-STS
        self.stored_energy = 0.5 * self.kt * (self.torsional_deflection**2)

        # Velocidade linear instantânea do centro da roda (CoR)
        v_linear_cor = effective_angular_speed * self.current_effective_radius
        return v_linear_cor, self.current_effective_radius, self.deceleration_spike

    @staticmethod
    def calculate_theoretical_csts_stiffness(thickness_mm: float, width_mm: float = 15.0, length_mm: float = 827.28):
        """
        Fórmula clássica de rigidez da mola espiral plana (Eq. 6 de Jeong & Kim, 2025):
        kt = (E * b * t^3) / (12 * L)
        """
        t = thickness_mm * 1e-3
        b = width_mm * 1e-3
        l = length_mm * 1e-3
        return (E_MODULUS_PLA * b * (t**3)) / (12.0 * l)
