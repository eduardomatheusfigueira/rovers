"""
Cinemática inversa 4WS — a MESMA formulação de `simulador_python/kinematics.py`.

Este módulo é deliberadamente puro (sem ROS) para poder ser testado contra a
implementação de referência do simulador. O nó ROS está em `no_cinematica.py`.

Convenção canônica: x para a frente, y para a esquerda, θ anti-horário.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

IDS = ("FL", "FR", "RL", "RR")
MODOS = ("ackermann", "crab", "spin", "stair")


@dataclass(frozen=True)
class Geometria:
    entre_eixos: float
    bitola: float
    raio_roda: float
    limite_estercamento: float

    def posicoes(self) -> Dict[str, Tuple[float, float]]:
        """Posições das rodas no referencial canônico (x frente, y esquerda)."""
        lf, lb = self.entre_eixos / 2.0, self.bitola / 2.0
        return {"FL": (+lf, +lb), "FR": (+lf, -lb), "RL": (-lf, +lb), "RR": (-lf, -lb)}


@dataclass
class Comando:
    angulos: Dict[str, float]        # rad, para os servos de esterçamento
    velocidades_rodas: Dict[str, float]   # rad/s, para os motores de tração
    saturado: bool
    icr: Tuple[float, float] | None


def resolver(geo: Geometria, vx: float, vy: float, omega: float,
             modo: str = "ackermann") -> Comando:
    """Resolve β_i e ω_i para o comando de corpo (vx, vy, ω) no modo dado.

    A velocidade do ponto de contato da roda i é v_i = v + ω × p_i:
        v_ix = vx − ω·y_i        v_iy = vy + ω·x_i
    e β_i = atan2(v_iy, v_ix). Essa é a única solução que faz as quatro normais
    convergirem num único ICR — ou seja, a única sem arrasto lateral.
    """
    if modo not in MODOS:
        raise ValueError(f"modo '{modo}' fora de {MODOS}")
    if modo == "stair":
        vy = omega = 0.0
    elif modo == "crab":
        omega = 0.0
    elif modo == "spin":
        vx = vy = 0.0

    angulos, velocidades = {}, {}
    saturado = False
    for wid, (px, py) in geo.posicoes().items():
        v_ix = vx - omega * py
        v_iy = vy + omega * px
        modulo = math.hypot(v_ix, v_iy)
        if modulo < 1e-9:
            beta, v = 0.0, 0.0
        else:
            beta = math.atan2(v_iy, v_ix)
            v = modulo
            if beta > math.pi / 2:
                beta -= math.pi
                v = -v
            elif beta < -math.pi / 2:
                beta += math.pi
                v = -v
            if abs(beta) > geo.limite_estercamento:
                saturado = True
                beta = math.copysign(geo.limite_estercamento, beta)
        angulos[wid] = beta
        velocidades[wid] = v / geo.raio_roda
    return Comando(angulos, velocidades, saturado, icr(vx, vy, omega))


def icr(vx: float, vy: float, omega: float):
    """Centro instantâneo de rotação; None em translação pura."""
    if abs(omega) < 1e-9:
        return None
    return (-vy / omega, vx / omega)


def residuo_deslizamento(geo: Geometria, cmd: Comando,
                         vx: float, vy: float, omega: float) -> float:
    """Maior componente de velocidade perpendicular ao plano de uma roda [m/s].

    Deve ser ~0 num comando bem resolvido. É a métrica que o supervisor publica
    para detectar descoordenação de servo em campo (ver 02_Engenharia/08 §3.5).
    """
    pior = 0.0
    for wid, (px, py) in geo.posicoes().items():
        v_ix = vx - omega * py
        v_iy = vy + omega * px
        b = cmd.angulos[wid]
        pior = max(pior, abs(-math.sin(b) * v_ix + math.cos(b) * v_iy))
    return pior


def tempo_reconfiguracao(geo: Geometria, de: Dict[str, float], para: Dict[str, float],
                         velocidade_servo: float) -> float:
    """Tempo para reorientar as rodas entre duas poses de esterçamento [s].

    Consequência de δs = 2: o rover NÃO é holonômico. Trocar de modo custa tempo
    e precisa acontecer com o veículo parado.
    """
    delta = max(abs(para[w] - de[w]) for w in IDS)
    return delta / max(velocidade_servo, 1e-6) + 0.10
