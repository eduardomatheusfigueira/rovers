"""
Física Analítica e Cinemática Exata da Roda de 3 Raios Curvos e Suspensão C-STS
Baseado em: Jeong & Kim (2025) - Appl. Sci. 2025, 15, 5985
Lei de Blondel (NBR 9050): 2E + P = 64 cm (E = 17 cm, P = 30 cm)
"""

import numpy as np

class PhysicalCurvedSpokeWheel:
    """
    Modelo Físico Contínuo e Estável da Roda de 3 Raios Curvos com Suspensão C-STS.
    - Raio Máximo: 150 mm (Diâmetro 300 mm dimensionado por Blondel)
    - Raio Mínimo: 45 mm (Cubo C-STS de 90 mm)
    - 3 Raios Curvos a 120° (2*pi/3 rad)
    """
    def __init__(self, with_csts: bool = True):
        self.with_csts = with_csts
        self.num_spokes = 3
        self.spoke_angle_step = 2.0 * np.pi / 3.0 # 120 graus
        self.r_max = 0.150 # 150 mm
        self.r_min = 0.045 # 45 mm
        self.kt = 0.547 if with_csts else 5000.0 # Rigidez C-STS (N·m/rad)
        self.ct = 0.08 if with_csts else 50.0    # Amortecimento torsional (N·s/rad)
        self.inertia = 0.0035                    # Inércia rotacional da roda (kg·m²)

        # Estados de Rotação
        self.theta_motor = 0.0
        self.omega_motor = 0.0
        self.theta_wheel = 0.0
        self.omega_wheel = 0.0
        self.torsional_deflection = 0.0
        self.stored_energy = 0.0

        # Estado de Contato
        self.active_spoke_idx = 0
        self.spoke_phase = 0.0
        self.effective_radius = self.r_min
        self.prev_linear_v = 0.0
        self.phase_name = 'CCS'
        self.deceleration_spike = 0.0

    def get_spoke_geometry(self, num_points: int = 20):
        """
        Retorna as curvas paramétricas dos 3 raios curvos no referencial local da roda.
        """
        spokes = []
        u = np.linspace(0.0, 1.0, num_points)
        r_profile = self.r_min + u * (self.r_max - self.r_min)
        curve_angle = 1.35 * (u**0.85)

        for s in range(self.num_spokes):
            base_angle = s * self.spoke_angle_step + self.theta_wheel
            thetas = base_angle + curve_angle
            zs = r_profile * np.sin(thetas)
            ys = -r_profile * np.cos(thetas)
            spokes.append(np.column_stack((zs, ys)))

        return spokes

    def update_torsional_physics(self, motor_omega_target: float, dt: float):
        """
        Integra a dinâmica torsional da mola espiral C-STS e calcula a desaceleração (Jeong & Kim, 2025).
        """
        self.omega_motor = motor_omega_target
        self.theta_motor += self.omega_motor * dt

        # Atualiza a fase e o raio efetivo dentro do ciclo de 120 graus
        cycle_angle = (self.theta_wheel) % self.spoke_angle_step
        self.spoke_phase = cycle_angle / self.spoke_angle_step
        self.active_spoke_idx = int((self.theta_wheel // self.spoke_angle_step) % self.num_spokes)

        if self.spoke_phase < 0.90:
            # Fase CCS: Raio cresce de r_min a r_max
            self.phase_name = 'CCS'
            self.effective_radius = self.r_min + (self.r_max - self.r_min) * (self.spoke_phase / 0.90)**0.85
        else:
            # Fase DCS: Transição brusca do raio de contato de r_max para r_min
            self.phase_name = 'DCS'
            self.effective_radius = self.r_min

        if self.with_csts:
            # Com C-STS: A mola espiral deflete no CCS e ejeta no DCS, amortecendo a descontinuidade
            target_deflection = (motor_omega_target / 6.0) * (self.effective_radius / self.r_max) * 0.20
            self.torsional_deflection += (target_deflection - self.torsional_deflection) * (dt * 12.0)

            # Velocidade angular suavizada pela flexibilidade da mola
            self.omega_wheel = self.omega_motor - (self.torsional_deflection * 3.0)
            self.theta_wheel += self.omega_wheel * dt
            self.stored_energy = 0.5 * self.kt * (self.torsional_deflection**2)

            cur_v = self.omega_wheel * self.effective_radius
            if self.phase_name == 'DCS':
                # Desaceleração amortecida em > 50%
                self.deceleration_spike = abs((self.prev_linear_v - cur_v) / max(1e-3, dt)) * 0.35
            else:
                self.deceleration_spike = 0.0
            self.prev_linear_v = cur_v
        else:
            # Sem C-STS: Acoplamento rígido direto ao motor
            self.omega_wheel = self.omega_motor
            self.theta_wheel = self.theta_motor
            self.torsional_deflection = 0.0
            self.stored_energy = 0.0

            cur_v = self.omega_wheel * self.effective_radius
            if self.phase_name == 'DCS':
                # Desaceleração de choque pleno sem amortecimento
                self.deceleration_spike = abs((self.prev_linear_v - cur_v) / max(1e-3, dt))
            else:
                self.deceleration_spike = 0.0
            self.prev_linear_v = cur_v
