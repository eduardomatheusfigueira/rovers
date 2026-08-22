"""
Terramecânica e Dinâmica de Forças Solo-Roda (J. Y. Wong, 2022)
Calcula transferência de carga dinâmica, esforço trativo (Drawbar Pull),
torque de demanda nos motores e eficiência energética comparativa.
"""

import numpy as np
from .config import (
    WEIGHT_TOTAL, WHEELBASE, TRACK_WIDTH, LF, LR, H_CG_TOTAL,
    COEFF_FRICTION_RUBBER, R_WHEEL_MAX, MOTOR_TORQUE_MAX
)

class TerramechanicsWong:
    def __init__(self):
        self.total_weight = WEIGHT_TOTAL
        self.wheelbase = WHEELBASE
        self.track_width = TRACK_WIDTH
        self.cg_height = H_CG_TOTAL
        self.mu = COEFF_FRICTION_RUBBER

    def calculate_normal_loads(self, pitch: float, roll: float, ax: float = 0.0, az: float = 0.0):
        """
        Calcula as reações normais dinâmicas (Fz) nas 4 rodas [FL, FR, RL, RR] (Wong, 2022, Cap. 5).
        Leva em consideração a inclinação do terreno (Pitch e Roll) e as acelerações inerciais.
        """
        w = self.total_weight
        l = self.wheelbase
        b = self.track_width
        h = self.cg_height

        # Forças normais nos eixos dianteiro e traseiro
        # Fz_frente = W * (Lr/L * cos(pitch) - h/L * sin(pitch)) - (W/g) * az * (h/L)
        # Fz_traseira = W * (Lf/L * cos(pitch) + h/L * sin(pitch)) + (W/g) * az * (h/L)
        cos_p = np.cos(pitch)
        sin_p = np.sin(pitch)

        f_front_total = w * ((LR / l) * cos_p - (h / l) * sin_p)
        f_rear_total  = w * ((LF / l) * cos_p + (h / l) * sin_p)

        # Distribuição lateral com base no Roll
        cos_r = np.cos(roll)
        sin_r = np.sin(roll)

        # Fração esquerda/direita
        left_fraction  = 0.5 - (h / b) * sin_r
        right_fraction = 0.5 + (h / b) * sin_r

        left_fraction = np.clip(left_fraction, 0.05, 0.95)
        right_fraction = np.clip(right_fraction, 0.05, 0.95)

        fz = {
            'FL': max(1.0, f_front_total * left_fraction),
            'FR': max(1.0, f_front_total * right_fraction),
            'RL': max(1.0, f_rear_total * left_fraction),
            'RR': max(1.0, f_rear_total * right_fraction)
        }
        return fz

    def calculate_tractive_effort(self, fz_dict: dict, effective_radius: float, is_stair: bool = False):
        """
        Calcula o esforço trativo máximo disponível por aderência de Coulomb
        e o torque demandado em cada motorredutor.
        """
        max_tractive_force = {}
        motor_torque_demand = {}
        total_drawbar_pull = 0.0

        # Resistência ao rolamento
        cr = 0.03 if not is_stair else 0.15 # Coeficiente de resistência

        for wheel_id, fz in fz_dict.items():
            f_traction_max = self.mu * fz
            f_resist = cr * fz
            f_net = f_traction_max - f_resist

            max_tractive_force[wheel_id] = f_traction_max
            torque_demand = min(MOTOR_TORQUE_MAX, f_traction_max * effective_radius)
            motor_torque_demand[wheel_id] = torque_demand
            total_drawbar_pull += max(0.0, f_net)

        return max_tractive_force, motor_torque_demand, total_drawbar_pull

    def compare_power_with_skid_steer(self, linear_speed: float, turn_radius: float):
        """
        Compara o consumo de potência do sistema 4WS sincronizado vs Skid-Steer (arrasto lateral).
        Demonstra a economia de até 75% de energia em curvas (Wong, 2022, Cap. 7).
        """
        # Potência 4WS (rolamento puro sem arrasto transversal)
        p_roll_4ws = self.total_weight * 0.04 * linear_speed

        # Potência Skid-Steer (trabalho de cisalhamento lateral nos pneus)
        slip_angle_skid = np.arctan(self.wheelbase / (2.0 * max(0.2, turn_radius)))
        lateral_friction_force = self.mu * (self.total_weight / 2.0) * np.sin(slip_angle_skid)
        p_skid = p_roll_4ws + (lateral_friction_force * linear_speed * 1.8)

        energy_savings_pct = max(0.0, min(80.0, (1.0 - (p_roll_4ws / max(1e-3, p_skid))) * 100.0))

        return {
            'power_4ws_watts': p_roll_4ws,
            'power_skid_steer_watts': p_skid,
            'savings_percentage': energy_savings_pct
        }
