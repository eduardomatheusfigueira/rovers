"""
Simulador Dinâmico 6-DOF e Multicorpo do Rover Frugal 4WD/4WS
Totalmente integrado à Cinemática de Blondel e Física de Raios Curvos com C-STS.
"""

import numpy as np
from .config import (
    WHEEL_POSITIONS, WHEELBASE, TRACK_WIDTH, MASS_TOTAL,
    PENDULUM_ARM, PENDULUM_DAMPING, H_CG_TOTAL, R_WHEEL_MAX, R_WHEEL_MIN,
    STAIR_RISER, STAIR_TREAD, BLONDEL_VALUE, GRAVITY
)
from .kinematics import Kinematics4WS
from .terramechanics import TerramechanicsWong
from .spoke_contact_physics import PhysicalCurvedSpokeWheel

class RoverMultibodySimulator:
    def __init__(self, with_csts: bool = True):
        self.with_csts = with_csts
        self.kinematics = Kinematics4WS()
        self.terramechanics = TerramechanicsWong()

        # 4 Rodas Físicas de 3 Raios Curvos
        self.wheels = {
            'FL': PhysicalCurvedSpokeWheel(with_csts=with_csts),
            'FR': PhysicalCurvedSpokeWheel(with_csts=with_csts),
            'RL': PhysicalCurvedSpokeWheel(with_csts=with_csts),
            'RR': PhysicalCurvedSpokeWheel(with_csts=with_csts)
        }

        # Estado do Chassi (Coordenadas Mundiais)
        # Z: Avanço (Frente = -Z, Ré = +Z)
        # X: Lateral (Direita = +X, Esquerda = -X)
        # Y: Altura (Solo plano = -0.15 m)
        self.x = 0.0
        self.y = 0.0
        self.z = 0.8
        self.vx = 0.0
        self.vz = 0.0
        self.speed = 0.0

        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0

        # Pêndulo da Caixa Organizadora
        self.pendulum_pitch = 0.0
        self.pendulum_velocity = 0.0

        # Estados das Rodas
        self.axle_positions = {}
        self.wheel_heights = {'FL': 0.0, 'FR': 0.0, 'RL': 0.0, 'RR': 0.0}
        self.steer_angles = {'FL': 0.0, 'FR': 0.0, 'RL': 0.0, 'RR': 0.0}
        self.normal_forces = {'FL': 18.5, 'FR': 18.5, 'RL': 18.5, 'RR': 18.5}
        self.contact_states = {'FL': True, 'FR': True, 'RL': True, 'RR': True}

        # Configuração da Escada de Blondel
        self.stair_start_z = -2.0
        self.num_steps = 3

        self.time = 0.0
        self.history = {
            'time': [], 'x': [], 'y': [], 'z': [], 'speed': [],
            'pitch': [], 'roll': [], 'yaw': [], 'pendulum_pitch': [],
            'fz_fl': [], 'fz_fr': [], 'fz_rl': [], 'fz_rr': [],
            'wheel_angle_fl': [], 'csts_deflection_fl': [],
            'stored_energy_total': [], 'deceleration_spike_max': []
        }

    def reset(self, x: float = 0.0, z: float = 0.8, heading: float = 0.0):
        self.x = x
        self.z = z
        self.y = 0.0
        self.vx = 0.0
        self.vz = 0.0
        self.speed = 0.0
        self.yaw = heading
        self.pitch = 0.0
        self.roll = 0.0
        self.pendulum_pitch = 0.0
        self.pendulum_velocity = 0.0
        self.time = 0.0
        for w in self.wheels.values():
            w.theta_motor = 0.0
            w.theta_wheel = 0.0
            w.omega_motor = 0.0
            w.omega_wheel = 0.0
            w.torsional_deflection = 0.0

    def get_terrain_height_at(self, z: float):
        """
        Retorna a cota Y da superfície da Escada de Blondel no ponto Z.
        Solo base: Y = -0.15 m
        Degrau 1: Y = -0.15 + 0.17 = +0.02 m  (Z em [-2.3, -2.0])
        Degrau 2: Y = -0.15 + 0.34 = +0.19 m  (Z em [-2.6, -2.3])
        Degrau 3: Y = -0.15 + 0.51 = +0.36 m  (Z em [-2.9, -2.6])
        Patamar : Y = +0.36 m                 (Z <= -2.9)
        """
        if z <= self.stair_start_z - 3 * STAIR_TREAD:
            return -0.15 + 3 * STAIR_RISER # Patamar
        elif z <= self.stair_start_z - 2 * STAIR_TREAD:
            return -0.15 + 3 * STAIR_RISER # Degrau 3
        elif z <= self.stair_start_z - 1 * STAIR_TREAD:
            return -0.15 + 2 * STAIR_RISER # Degrau 2
        elif z <= self.stair_start_z:
            return -0.15 + 1 * STAIR_RISER # Degrau 1
        return -0.15 # Solo Plano

    def step(self, throttle_cmd: float, steer_cmd: float, mode: str = 'ackermann', dt: float = 0.01):
        """
        Executa um passo temporal completo e suave da física veicular.
        """
        self.time += dt

        # 1. Cinemática e Controle de Velocidade
        target_speed = throttle_cmd * 1.0 # m/s
        target_steer = steer_cmd * np.radians(40.0)

        if mode == 'spin':
            omega_cmd = steer_cmd * 1.4
            vx_cmd, vz_cmd = 0.0, 0.0
        elif mode == 'crab':
            omega_cmd = 0.0
            vx_cmd = np.sin(target_steer) * target_speed
            vz_cmd = np.cos(target_steer) * target_speed
        elif mode == 'stair':
            omega_cmd = 0.0
            vx_cmd = 0.0
            vz_cmd = target_speed * 0.70 # Avanço síncrono em escada
        else: # 'ackermann'
            omega_cmd = (target_speed / (WHEELBASE / 2.0)) * np.sin(target_steer)
            vx_cmd = 0.0
            vz_cmd = target_speed

        steer_angles, wheel_speeds, _ = self.kinematics.compute_inverse_kinematics(
            vx_cmd, vz_cmd, omega_cmd, mode=mode
        )
        self.steer_angles = steer_angles

        # 2. Integração Suave de Velocidade e Translação
        accel_rate = 3.5
        self.speed += (target_speed - self.speed) * min(1.0, dt * accel_rate)
        self.yaw += omega_cmd * dt

        if mode == 'crab':
            crab_h = self.yaw + target_steer
            self.x += -np.sin(crab_h) * self.speed * dt
            self.z += -np.cos(crab_h) * self.speed * dt
        elif mode == 'spin':
            pass
        else:
            self.x += -np.sin(self.yaw) * self.speed * dt
            self.z += -np.cos(self.yaw) * self.speed * dt

        # 3. Posições dos Eixos das Rodas no Espaço Longitudinal (Z)
        cos_p = np.cos(self.pitch)
        sin_p = np.sin(self.pitch)
        cos_y = np.cos(self.yaw)
        sin_y = np.sin(self.yaw)

        # Dianteiras (FL e FR) em Z_front, Traseiras (RL e RR) em Z_rear
        z_front_local = -WHEELBASE / 2.0
        z_rear_local  =  WHEELBASE / 2.0

        z_fl_world = self.z + z_front_local * cos_y * cos_p
        z_fr_world = self.z + z_front_local * cos_y * cos_p
        z_rl_world = self.z + z_rear_local  * cos_y * cos_p
        z_rr_world = self.z + z_rear_local  * cos_y * cos_p

        wheel_z_map = {'FL': z_fl_world, 'FR': z_fr_world, 'RL': z_rl_world, 'RR': z_rr_world}

        # 4. Atualização da Física de Rotação e Contato dos 3 Raios Curvos
        total_energy = 0.0
        max_decel_spike = 0.0
        target_axle_y = {}

        for w_id, wheel in self.wheels.items():
            w_speed = wheel_speeds[w_id]
            # Velocidade angular do motor: omega = v / r_eff
            target_motor_omega = w_speed / max(0.05, wheel.effective_radius)

            # Atualiza torção C-STS
            wheel.update_torsional_physics(target_motor_omega, dt)
            total_energy += wheel.stored_energy
            if wheel.deceleration_spike > max_decel_spike:
                max_decel_spike = wheel.deceleration_spike

            # Determina a altura da superfície no ponto da roda
            wz = wheel_z_map[w_id]
            ground_y = self.get_terrain_height_at(wz)

            # A cota do eixo da roda é dada pelo terreno + raio efetivo instantâneo do raio ativo!
            # Isso gera a suave ondulação cicloidal característica dos raios curvos
            spoke_roll_height = wheel.effective_radius
            target_axle_y[w_id] = ground_y + spoke_roll_height
            self.wheel_heights[w_id] = target_axle_y[w_id]

        # 5. Cinemática Multicorpo do Chassi
        front_y = (target_axle_y['FL'] + target_axle_y['FR']) / 2.0
        rear_y  = (target_axle_y['RL'] + target_axle_y['RR']) / 2.0
        left_y  = (target_axle_y['FL'] + target_axle_y['RL']) / 2.0
        right_y = (target_axle_y['FR'] + target_axle_y['RR']) / 2.0

        target_chassis_y = (front_y + rear_y) / 2.0
        target_pitch = np.arctan2(front_y - rear_y, WHEELBASE)
        target_roll  = np.arctan2(right_y - left_y, TRACK_WIDTH)

        # Filtro passa-baixa suave para amortecimento da suspensão
        self.y += (target_chassis_y - self.y) * min(1.0, dt * 10.0)
        self.pitch += (target_pitch - self.pitch) * min(1.0, dt * 8.0)
        self.roll += (target_roll - self.roll) * min(1.0, dt * 8.0)

        # 6. Balanço Pendular da Caixa Organizadora (Auto-Estabilização da Carga)
        pendulum_accel = -(GRAVITY / PENDULUM_ARM) * np.sin(self.pendulum_pitch - self.pitch) - PENDULUM_DAMPING * self.pendulum_velocity
        self.pendulum_velocity += pendulum_accel * dt
        self.pendulum_pitch += self.pendulum_velocity * dt

        # 7. Forças Normais Dinâmicas (Wong, 2022)
        self.normal_forces = self.terramechanics.calculate_normal_loads(self.pitch, self.roll)

        # 8. Gravação de Histórico
        self.history['time'].append(self.time)
        self.history['x'].append(self.x)
        self.history['y'].append(self.y)
        self.history['z'].append(self.z)
        self.history['speed'].append(self.speed)
        self.history['pitch'].append(np.degrees(self.pitch))
        self.history['roll'].append(np.degrees(self.roll))
        self.history['yaw'].append(np.degrees(self.yaw))
        self.history['pendulum_pitch'].append(np.degrees(self.pendulum_pitch))
        self.history['fz_fl'].append(self.normal_forces['FL'])
        self.history['fz_fr'].append(self.normal_forces['FR'])
        self.history['fz_rl'].append(self.normal_forces['RL'])
        self.history['fz_rr'].append(self.normal_forces['RR'])
        self.history['wheel_angle_fl'].append(np.degrees(self.wheels['FL'].theta_wheel))
        self.history['csts_deflection_fl'].append(np.degrees(self.wheels['FL'].torsional_deflection))
        self.history['stored_energy_total'].append(total_energy)
        self.history['deceleration_spike_max'].append(max_decel_spike)
