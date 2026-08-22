"""
Modelo de Terreno e Colisão de Rodas na Escada de Blondel (NBR 9050)
Calcula a altura do solo e o engate nos degraus para cada uma das 4 rodas independentes.
"""

import numpy as np
from .config import (
    STAIR_RISER, STAIR_TREAD, BLONDEL_VALUE, R_WHEEL_MAX,
    K_RUBBER_BAND, C_RUBBER_BAND, MAX_SUSP_TRAVEL
)

class BlondelStaircaseCollision:
    def __init__(self, stair_start_z: float = -2.0, num_steps: int = 3):
        self.riser = STAIR_RISER    # 0.17 m (Espelho E)
        self.tread = STAIR_TREAD    # 0.30 m (Piso P)
        self.blondel_value = BLONDEL_VALUE # 2E + P = 0.64 m
        self.stair_start_z = stair_start_z
        self.num_steps = num_steps
        self.stair_width = 2.0      # Largura da escada (m)
        self.base_ground_y = -0.15  # Cota do piso plano inferior (m)

    def get_terrain_height(self, x: float, z: float):
        """
        Retorna a cota de elevação Y do terreno na coordenada mundial (X, Z).
        """
        if abs(x) <= (self.stair_width / 2.0):
            # Verificar se está na região longitudinal da escadaria
            for step_idx in range(self.num_steps):
                step_z_start = self.stair_start_z - step_idx * self.tread
                step_z_end   = self.stair_start_z - (step_idx + 1) * self.tread

                if step_z_end <= z <= step_z_start:
                    # Degrau step_idx + 1
                    return self.base_ground_y + (step_idx + 1) * self.riser

            # Se ultrapassou o último degrau (Patamar Superior)
            platform_start_z = self.stair_start_z - self.num_steps * self.tread
            if z <= platform_start_z:
                return self.base_ground_y + self.num_steps * self.riser

        return self.base_ground_y

    def evaluate_wheel_collision(self, wheel_world_pos: np.ndarray, wheel_prev_y: float, dt: float):
        """
        Avalia o contato e a reação da suspensão por elásticos para uma roda individual.
        wheel_world_pos: [X, Y, Z]
        """
        wx, wy, wz = wheel_world_pos[0], wheel_world_pos[1], wheel_world_pos[2]
        terrain_y = self.get_terrain_height(wx, wz)

        # A altura ideal da manga da roda é terreno_y + raio_roda
        target_wheel_y = terrain_y + R_WHEEL_MAX

        # Deformação da suspensão por elásticos (linear)
        # Delta_y = target_wheel_y - wy
        penetration = target_wheel_y - wy

        if penetration > 0:
            # Roda apoiada no solo/degrau (compressão dos elásticos)
            susp_travel = np.clip(penetration, 0.0, MAX_SUSP_TRAVEL)
            susp_velocity = (target_wheel_y - wheel_prev_y) / max(1e-4, dt)

            # Força elástica + amortecimento viscoso do feixe de elásticos
            f_spring = K_RUBBER_BAND * susp_travel
            f_damp = C_RUBBER_BAND * susp_velocity
            f_contact = max(0.0, f_spring + f_damp)
            is_contact = True
            actual_wheel_y = target_wheel_y
        else:
            # Roda no ar (sem contato)
            f_contact = 0.0
            is_contact = False
            actual_wheel_y = wy - 9.81 * (dt**2) # Queda livre

        return actual_wheel_y, f_contact, is_contact, terrain_y
