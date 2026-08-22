"""
Cinemática Omnidirecional 4WD / 4WS (Siegwart & Nourbakhsh, 2004)
Grau de Mobilidade delta_m = 2, Dirigibilidade delta_s = 4, Manobrabilidade delta_M = 3.
Calcula a cinemática inversa para cada uma das 4 rodas orientáveis independentes.
"""

import numpy as np
from .config import WHEEL_POSITIONS, R_WHEEL_MAX, MAX_STEER_ANGLE, WHEELBASE, TRACK_WIDTH

class Kinematics4WS:
    def __init__(self):
        self.modes = ['ackermann', 'crab', 'spin', 'stair']
        self.current_mode = 'ackermann'

    def compute_inverse_kinematics(self, vx_cmd: float, vz_cmd: float, omega_cmd: float, mode: str = None):
        """
        Calcula os ângulos de esterçamento (beta_i) e as velocidades lineares/angulares
        de cada uma das 4 rodas para atender aos comandos [vx, vz, omega].

        Convenção de coordenadas do robô:
        - +Z: Traseira, -Z: Frente (vx: velocidade longitudinal ao longo de -Z)
        - +X: Direita, -X: Esquerda
        - omega: velocidade angular de guinada (Yaw) em torno do eixo Y
        """
        if mode is None:
            mode = self.current_mode
        else:
            self.current_mode = mode

        steer_angles = {}
        wheel_speeds = {}
        wheel_rpms = {}

        if mode == 'stair':
            # Modo Escada: Rodas alinhadas estritamente a 0° com tração síncrona
            for wheel_id in ['FL', 'FR', 'RL', 'RR']:
                steer_angles[wheel_id] = 0.0
                wheel_speeds[wheel_id] = vz_cmd
                wheel_rpms[wheel_id] = (vz_cmd / (2.0 * np.pi * R_WHEEL_MAX)) * 60.0
            return steer_angles, wheel_speeds, wheel_rpms

        elif mode == 'crab':
            # Modo Caranguejo: 4 rodas esterçadas no mesmo ângulo para translação pura
            steer_angle = np.clip(np.arctan2(vx_cmd, vz_cmd if abs(vz_cmd) > 1e-4 else 1e-4), -MAX_STEER_ANGLE, MAX_STEER_ANGLE)
            total_speed = np.hypot(vx_cmd, vz_cmd) * np.sign(vz_cmd if abs(vz_cmd) > 1e-4 else 1.0)
            for wheel_id in ['FL', 'FR', 'RL', 'RR']:
                steer_angles[wheel_id] = steer_angle
                wheel_speeds[wheel_id] = total_speed
                wheel_rpms[wheel_id] = (total_speed / (2.0 * np.pi * R_WHEEL_MAX)) * 60.0
            return steer_angles, wheel_speeds, wheel_rpms

        elif mode == 'spin':
            # Giro em Torno do Próprio Eixo (Raio Zero): 4 rodas tangenciais
            # Ângulos tangenciais aos vértices do retângulo em X
            # FL: +45°, FR: -45°, RL: -45°, RR: +45°
            spin_angle = np.arctan2(WHEELBASE / 2.0, TRACK_WIDTH / 2.0)
            steer_angles['FL'] = spin_angle
            steer_angles['FR'] = -spin_angle
            steer_angles['RL'] = -spin_angle
            steer_angles['RR'] = spin_angle

            spin_linear_speed = omega_cmd * np.hypot(TRACK_WIDTH / 2.0, WHEELBASE / 2.0)
            for wheel_id in ['FL', 'FR', 'RL', 'RR']:
                wheel_speeds[wheel_id] = spin_linear_speed
                wheel_rpms[wheel_id] = (spin_linear_speed / (2.0 * np.pi * R_WHEEL_MAX)) * 60.0
            return steer_angles, wheel_speeds, wheel_rpms

        else: # 'ackermann'
            # Ackermann Duplo com Contragiro Traseiro (Curva Sincronizada sem Arrasto Lateral)
            for wheel_id, pos in WHEEL_POSITIONS.items():
                xi = pos[0] # Posição lateral
                zi = pos[2] # Posição longitudinal

                # Vetor de velocidade local no ponto de contato da roda i:
                # v_ix = vx - omega * zi
                # v_iz = vz + omega * xi
                v_ix = vx_cmd - omega_cmd * zi
                v_iz = vz_cmd + omega_cmd * xi

                # Ângulo de esterçamento da roda i:
                if abs(v_iz) > 1e-4 or abs(v_ix) > 1e-4:
                    raw_steer = np.arctan2(v_ix, v_iz)
                    # Limitar à faixa máxima de esterçamento
                    steer_angles[wheel_id] = np.clip(raw_steer, -MAX_STEER_ANGLE, MAX_STEER_ANGLE)
                else:
                    steer_angles[wheel_id] = 0.0

                v_linear = np.hypot(v_ix, v_iz) * np.sign(v_iz if abs(v_iz) > 1e-4 else (v_ix if abs(v_ix) > 1e-4 else 1.0))
                wheel_speeds[wheel_id] = v_linear
                wheel_rpms[wheel_id] = (v_linear / (2.0 * np.pi * R_WHEEL_MAX)) * 60.0

            return steer_angles, wheel_speeds, wheel_rpms

    def compute_icr(self, vx: float, vz: float, omega: float):
        """
        Calcula as coordenadas do Centro Instantâneo de Rotação (ICR) no plano [X, Z].
        """
        if abs(omega) < 1e-5:
            return None # Raio infinito (linha reta)
        x_icr = -vz / omega
        z_icr = vx / omega
        return (x_icr, z_icr)
