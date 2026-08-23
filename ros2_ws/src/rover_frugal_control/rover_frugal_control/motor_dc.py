"""
Modelo do motorredutor, da bateria e do aquecimento — espelho de
`simulador_python/powertrain.py`, em Python puro e sem ROS.

**Por que isso precisa existir na simulação.** Sem ele, o `ros2_control` comanda
velocidade e o Gazebo entrega qualquer torque até o limite da junta — ou seja, o
motor simulado teria torque de stall a 1,5 m/s, o que é fisicamente impossível.
O rover subiria escadas que o motorredutor real não sustenta, e a margem de
torque de 1,61 calculada no dimensionamento nunca seria testada.

Com este modelo, três limites da análise passam a valer dentro do simulador:

1. **Curva torque-velocidade.** T disponível cai com ω; a 1,53 m/s é zero.
2. **Queda de tensão do pack.** 28,6 A de pico sobre 50 mΩ derrubam a tensão e,
   com ela, o torque disponível.
3. **Limite térmico.** Em escada o motor opera a ~11% de rendimento; o limite da
   missão é térmico, não energético.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MotorCC:
    """Motor CC de ímã permanente com redutor planetário, no eixo de saída."""

    tensao_nominal: float = 12.0
    kv_rpm_por_volt: float = 1000.0
    resistencia: float = 1.10
    corrente_vazio: float = 0.35
    reducao: float = 172.0
    eficiencia_reducao: float = 0.72
    limite_corrente: float = 20.0

    @property
    def kt(self) -> float:
        """Constante de torque [N·m/A] = constante de fcem [V·s/rad]."""
        return 60.0 / (2.0 * math.pi * self.kv_rpm_por_volt)

    @property
    def torque_stall_saida(self) -> float:
        i = self.tensao_nominal / self.resistencia
        return self.kt * (i - self.corrente_vazio) * self.reducao * self.eficiencia_reducao

    @property
    def omega_vazio_saida(self) -> float:
        return (self.kv_rpm_por_volt * self.tensao_nominal / self.reducao) * 2.0 * math.pi / 60.0

    def torque_disponivel(self, omega_saida: float, tensao: float | None = None) -> float:
        """Torque máximo no eixo de saída para a rotação e tensão dadas."""
        v = self.tensao_nominal if tensao is None else tensao
        fcem = self.kt * abs(omega_saida) * self.reducao
        corrente = min(self.limite_corrente, max(0.0, (v - fcem) / self.resistencia))
        return self.kt * max(0.0, corrente - self.corrente_vazio) \
            * self.reducao * self.eficiencia_reducao

    def corrente_para_torque(self, torque_saida: float) -> float:
        rotor = abs(torque_saida) / (self.reducao * self.eficiencia_reducao)
        return rotor / self.kt + self.corrente_vazio


@dataclass
class PackBateria:
    serie: int = 4
    paralelo: int = 2
    capacidade_celula_ah: float = 3.0
    tensao_nominal_celula: float = 3.2
    tensao_cheia_celula: float = 3.65
    tensao_corte_celula: float = 2.80
    r_interna_celula: float = 0.025
    soc: float = 1.0
    consumido_wh: float = 0.0

    @property
    def capacidade_ah(self) -> float:
        return self.paralelo * self.capacidade_celula_ah

    @property
    def r_interna(self) -> float:
        return self.r_interna_celula * self.serie / self.paralelo

    @property
    def energia_wh(self) -> float:
        return self.capacidade_ah * self.serie * self.tensao_nominal_celula

    def tensao(self, corrente: float) -> float:
        ocv = (self.tensao_corte_celula
               + (self.tensao_cheia_celula - self.tensao_corte_celula)
               * (0.15 + 0.85 * max(0.0, min(1.0, self.soc))))
        return max(self.serie * self.tensao_corte_celula,
                   self.serie * ocv - corrente * self.r_interna)

    def consumir(self, potencia_w: float, dt: float) -> None:
        self.consumido_wh += potencia_w * dt / 3600.0
        self.soc = max(0.0, 1.0 - self.consumido_wh / self.energia_wh)

    def taxa_c(self, corrente: float) -> float:
        return corrente / self.capacidade_ah


@dataclass
class Termica:
    """Primeira ordem no enrolamento — mesmo modelo do supervisor."""

    resistencia: float = 1.10
    r_termica: float = 8.0
    c_termica: float = 30.0
    ambiente: float = 35.0
    limite: float = 115.0
    temperatura: float = field(default=35.0)

    def passo(self, corrente: float, dt: float) -> float:
        regime = self.ambiente + corrente ** 2 * self.resistencia * self.r_termica
        self.temperatura += (regime - self.temperatura) * (dt / (self.r_termica * self.c_termica))
        return self.temperatura

    @property
    def fracao(self) -> float:
        return (self.temperatura - self.ambiente) / (self.limite - self.ambiente)


@dataclass
class ControleTracao:
    """PI de velocidade saturado pela curva do motor.

    A saturação não é um `clip` arbitrário: é o torque que o motorredutor
    **consegue** entregar naquela rotação e naquela tensão de pack.
    """

    motor: MotorCC
    kp: float = 4.0
    ki: float = 12.0
    integral: float = 0.0
    limite_integral: float = 5.0

    def passo(self, omega_desejada: float, omega_medida: float,
              tensao: float, dt: float, fator_torque: float = 1.0) -> tuple[float, float]:
        """Devolve (torque comandado, corrente estimada)."""
        erro = omega_desejada - omega_medida
        self.integral = max(-self.limite_integral,
                            min(self.limite_integral, self.integral + erro * dt))
        torque = self.kp * erro + self.ki * self.integral

        disponivel = self.motor.torque_disponivel(omega_medida, tensao) * fator_torque
        if abs(torque) > disponivel:
            torque = math.copysign(disponivel, torque)
            # Anti-windup: sem isso o integrador acumula durante a saturação em
            # escada e o rover dispara quando a roda finalmente engata.
            self.integral -= erro * dt
        return torque, self.motor.corrente_para_torque(torque)
