"""
Supervisor de segurança — a máquina de estados de `02_Engenharia/08`, em Python
puro para poder ser testada sem simulador nem hardware.

Implementa as três proteções que a análise física de R2 tornou obrigatórias:

1. **Limiar anti-tombamento dependente de modo.** Numa escada de 29,5° a marcha
   de 3 raios leva o chassi a ~43° de arfagem em operação NORMAL; um limiar
   único de 40° abortaria toda subida.
2. **Proteção térmica por integral I²t.** O dano ao esmalte é integral: desarmar
   por corrente instantânea não protege. Em escada o motor opera a ~11% de
   rendimento e o limite de missão é térmico, não energético.
3. **Failsafe com freio dinâmico.** Cortar o PWM e deixar as rodas livres em
   rampa faz o rover descer sozinho.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class Estado(Enum):
    BOOT = "BOOT"
    AUTOTESTE = "AUTOTESTE"
    ARMADO = "ARMADO"
    OPERACAO_PLANO = "OPERACAO_PLANO"
    RECONFIGURANDO = "RECONFIGURANDO"
    OPERACAO_ESCADA = "OPERACAO_ESCADA"
    RESFRIAMENTO = "RESFRIAMENTO"
    FAILSAFE = "FAILSAFE"
    PROTECAO = "PROTECAO"
    FALHA = "FALHA"


@dataclass
class ModeloTermico:
    """Primeira ordem no enrolamento: o mesmo de `simulador_python.powertrain`."""

    resistencia: float = 1.10
    r_termica: float = 8.0
    c_termica: float = 30.0
    ambiente: float = 35.0
    limite: float = 115.0
    retomada: float = 90.0
    temperatura: float = field(default=35.0)

    def passo(self, corrente: float, dt: float) -> float:
        regime = self.ambiente + corrente ** 2 * self.resistencia * self.r_termica
        tau = self.r_termica * self.c_termica
        self.temperatura += (regime - self.temperatura) * (dt / tau)
        return self.temperatura


@dataclass
class Limites:
    pitch_plano_deg: float = 35.0
    pitch_escada_deg: float = 52.0
    roll_deg: float = 30.0
    timeout_enlace_s: float = 0.30
    choque_carga_g: float = 2.0


@dataclass
class Entradas:
    arfagem_deg: float = 0.0
    rolagem_deg: float = 0.0
    corrente_por_motor: float = 0.0
    idade_enlace_s: float = 0.0
    modo: str = "ackermann"
    rearme_solicitado: bool = False
    autoteste_ok: bool = True
    piso_seco_confirmado: bool = False


@dataclass
class Saidas:
    estado: Estado
    tracao_liberada: bool
    freio_dinamico: bool
    fator_torque: float
    alertas: list


class Supervisor:
    def __init__(self, limites: Limites | None = None,
                 termico: ModeloTermico | None = None) -> None:
        self.lim = limites or Limites()
        self.termico = termico or ModeloTermico()
        self.estado = Estado.BOOT

    def limiar_arfagem(self, modo: str) -> float:
        return (self.lim.pitch_escada_deg if modo == "stair"
                else self.lim.pitch_plano_deg)

    def passo(self, e: Entradas, dt: float) -> Saidas:
        alertas = []
        self.termico.passo(e.corrente_por_motor, dt)

        if self.estado is Estado.BOOT:
            self.estado = Estado.AUTOTESTE
        elif self.estado is Estado.AUTOTESTE:
            self.estado = Estado.ARMADO if e.autoteste_ok else Estado.FALHA

        # As condições de proteção têm precedência sobre qualquer operação.
        if e.idade_enlace_s > self.lim.timeout_enlace_s:
            self.estado = Estado.FAILSAFE
            alertas.append("enlace perdido")
        elif abs(e.arfagem_deg) > self.limiar_arfagem(e.modo):
            self.estado = Estado.PROTECAO
            alertas.append(f"arfagem {e.arfagem_deg:.0f}° acima do limiar "
                           f"{self.limiar_arfagem(e.modo):.0f}° (modo {e.modo})")
        elif abs(e.rolagem_deg) > self.lim.roll_deg:
            self.estado = Estado.PROTECAO
            alertas.append(f"rolagem {e.rolagem_deg:.0f}° acima do limiar")
        elif self.termico.temperatura >= self.termico.limite:
            self.estado = Estado.RESFRIAMENTO
            alertas.append(f"enrolamento a {self.termico.temperatura:.0f} °C — I²t")
        elif self.estado is Estado.RESFRIAMENTO:
            if self.termico.temperatura < self.termico.retomada:
                self.estado = (Estado.OPERACAO_ESCADA if e.modo == "stair"
                               else Estado.OPERACAO_PLANO)
            else:
                alertas.append("resfriando")
        elif self.estado in (Estado.FAILSAFE, Estado.PROTECAO):
            # Rearme SEMPRE explícito: um rover que sai da parada de emergência
            # sozinho é um rover que atropela alguém enquanto o piloto olha para
            # o outro lado.
            if e.rearme_solicitado:
                self.estado = Estado.ARMADO
            else:
                alertas.append("aguardando rearme do piloto")
        elif self.estado in (Estado.ARMADO, Estado.OPERACAO_PLANO, Estado.OPERACAO_ESCADA):
            if e.modo == "stair":
                if not e.piso_seco_confirmado:
                    self.estado = Estado.ARMADO
                    alertas.append("modo escada bloqueado: confirme piso seco "
                                   "(μ exigido 0,72; concreto molhado dá 0,55)")
                else:
                    self.estado = Estado.OPERACAO_ESCADA
            else:
                self.estado = Estado.OPERACAO_PLANO

        operando = self.estado in (Estado.OPERACAO_PLANO, Estado.OPERACAO_ESCADA)
        fator = 1.0
        if self.termico.temperatura > self.termico.limite - 15.0:
            fator = 0.5
            alertas.append("torque reduzido por temperatura")

        return Saidas(
            estado=self.estado,
            tracao_liberada=operando,
            freio_dinamico=self.estado in (Estado.FAILSAFE, Estado.PROTECAO),
            fator_torque=fator if operando else 0.0,
            alertas=alertas,
        )
