"""
Cinemática 4WD/4WS segundo Siegwart & Nourbakhsh (2004), cap. 3.

CONVENÇÃO CANÔNICA DO REFERENCIAL DO ROBÔ (usada em todo este módulo):
    x_R -> frente        y_R -> esquerda        θ -> guinada anti-horária

A conversão para o referencial de renderização do protótipo 3D (Three.js, onde
+X é a direita, +Y é para cima e a frente é -Z) é feita por `para_referencial_render`.
A mistura silenciosa dessas duas convenções era uma fonte de erro de sinal no
código original; aqui ela é explícita.

CLASSIFICAÇÃO CINEMÁTICA
------------------------
Para cada roda direcional padrão i em coordenadas polares (l_i, α_i) com ângulo
de esterçamento β_i e raio r:

    rolamento :  [ sin(α+β)   −cos(α+β)   −l·cos β ] · ξ̇_R = r·φ̇_i
    deslizamento: [ cos(α+β)    sin(α+β)    l·sin β ] · ξ̇_R = 0

O grau de mobilidade é δm = 3 − posto(C1s) e o de dirigibilidade δs = posto(C1s),
com δM = δm + δs. A função `classificar_siegwart` calcula esses postos
numericamente — e mostra que o rover é da categoria "Two-Steer" (δm=1, δs=2,
δM=3), NÃO holonômico: ele consegue qualquer movimento no plano, mas precisa
reorientar as rodas antes de mudar de direção instantânea.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from .config import P as PARAMS

IDS = ("FL", "FR", "RL", "RR")
MODOS = ("ackermann", "crab", "spin", "stair")


def posicoes_rodas(entre_eixos: float = None, bitola: float = None) -> Dict[str, np.ndarray]:
    """Posições das rodas no referencial canônico (x frente, y esquerda)."""
    L = PARAMS.veiculo.entre_eixos_L if entre_eixos is None else entre_eixos
    W = PARAMS.veiculo.bitola_W if bitola is None else bitola
    return {
        "FL": np.array([+L / 2.0, +W / 2.0]),
        "FR": np.array([+L / 2.0, -W / 2.0]),
        "RL": np.array([-L / 2.0, +W / 2.0]),
        "RR": np.array([-L / 2.0, -W / 2.0]),
    }


def para_referencial_render(p: np.ndarray) -> np.ndarray:
    """(x_frente, y_esquerda) -> (X_direita, Z_ré) do protótipo 3D."""
    return np.array([-p[1], -p[0]])


# =============================================================================
# 1. CINEMÁTICA INVERSA
# =============================================================================
@dataclass
class ComandoRodas:
    angulos: Dict[str, float]        # β_i [rad]
    velocidades: Dict[str, float]    # v_i [m/s] na periferia da roda
    rpm: Dict[str, float]
    icr: Optional[Tuple[float, float]]
    modo: str
    saturado: bool                   # algum β_i excedeu o limite mecânico

    def como_arrays(self):
        return (np.array([self.angulos[i] for i in IDS]),
                np.array([self.velocidades[i] for i in IDS]))


class Cinematica4WS:
    """Cinemática inversa/direta e verificação de restrições."""

    def __init__(self, entre_eixos: float = None, bitola: float = None,
                 raio_roda: float = None, angulo_max: float = None):
        self.pos = posicoes_rodas(entre_eixos, bitola)
        self.L = PARAMS.veiculo.entre_eixos_L if entre_eixos is None else entre_eixos
        self.W = PARAMS.veiculo.bitola_W if bitola is None else bitola
        self.r = PARAMS.roda.raio_max if raio_roda is None else raio_roda
        self.beta_max = (np.radians(PARAMS.estercamento.angulo_maximo_deg)
                         if angulo_max is None else angulo_max)

    # --- inversa ------------------------------------------------------------
    def inversa(self, vx: float, vy: float, omega: float, modo: str = "ackermann") -> ComandoRodas:
        """Resolve β_i e v_i para o comando de corpo (vx, vy, ω).

        A velocidade do ponto de contato da roda i é v_i = v + ω × p_i, ou seja
            v_ix = vx − ω·y_i        v_iy = vy + ω·x_i
        e o ângulo da roda é β_i = atan2(v_iy, v_ix). Essa é a única solução que
        alinha as quatro normais num único ICR — não há arrasto lateral.
        """
        if modo not in MODOS:
            raise ValueError(f"Modo '{modo}' fora de {MODOS}")

        if modo == "stair":
            vy, omega = 0.0, 0.0                # eixos travados a 0°, tração síncrona
        elif modo == "crab":
            omega = 0.0                         # translação pura
        elif modo == "spin":
            vx = vy = 0.0                       # rotação pura em torno do CG

        angulos, velocidades, rpms = {}, {}, {}
        saturado = False
        for wid, p in self.pos.items():
            v_ix = vx - omega * p[1]
            v_iy = vy + omega * p[0]
            modulo = float(np.hypot(v_ix, v_iy))

            if modulo < 1e-9:
                beta, v_signed = 0.0, 0.0
            else:
                beta = float(np.arctan2(v_iy, v_ix))
                # Normaliza para |β| <= 90° invertendo o sentido de rotação da roda
                v_signed = modulo
                if beta > np.pi / 2:
                    beta, v_signed = beta - np.pi, -modulo
                elif beta < -np.pi / 2:
                    beta, v_signed = beta + np.pi, -modulo
                if abs(beta) > self.beta_max:
                    saturado = True
                    beta = float(np.clip(beta, -self.beta_max, self.beta_max))

            angulos[wid] = beta
            velocidades[wid] = v_signed
            rpms[wid] = v_signed / (2.0 * np.pi * self.r) * 60.0

        return ComandoRodas(angulos, velocidades, rpms,
                            self.icr(vx, vy, omega), modo, saturado)

    # --- ICR ----------------------------------------------------------------
    @staticmethod
    def icr(vx: float, vy: float, omega: float) -> Optional[Tuple[float, float]]:
        """Centro Instantâneo de Rotação no referencial do robô.

        O ICR é o ponto de velocidade nula: v + ω × p = 0  =>  p = (−vy/ω, vx/ω).
        """
        if abs(omega) < 1e-9:
            return None                      # translação pura: ICR no infinito
        return (-vy / omega, vx / omega)

    # --- verificação --------------------------------------------------------
    def residuo_deslizamento(self, cmd: ComandoRodas, vx: float, vy: float,
                             omega: float) -> np.ndarray:
        """Componente de velocidade PERPENDICULAR ao plano de cada roda [m/s].

        Deve ser ~0 para um comando bem resolvido: é a prova numérica de que o
        4WS coordenado elimina o arrasto lateral (ao contrário do skid-steer,
        cujo resíduo é da ordem da própria velocidade do veículo).
        """
        res = []
        for wid, p in self.pos.items():
            v_ix = vx - omega * p[1]
            v_iy = vy + omega * p[0]
            beta = cmd.angulos[wid]
            res.append(float(-np.sin(beta) * v_ix + np.cos(beta) * v_iy))
        return np.array(res)

    def direta(self, angulos: Dict[str, float], velocidades: Dict[str, float]) -> np.ndarray:
        """Odometria: estima (vx, vy, ω) por mínimos quadrados das quatro rodas.

        Cada roda fornece a projeção da sua velocidade no próprio plano:
            v_i = cos(β_i)·vx + sin(β_i)·vy + (x_i·sin β_i − y_i·cos β_i)·ω
        Com quatro rodas o sistema é sobredeterminado (4x3): o resíduo dos
        mínimos quadrados é o indicador de escorregamento a ser monitorado pela
        telemetria embarcada.
        """
        A = np.array([[np.cos(angulos[w]), np.sin(angulos[w]),
                       self.pos[w][0] * np.sin(angulos[w]) - self.pos[w][1] * np.cos(angulos[w])]
                      for w in IDS])
        b = np.array([velocidades[w] for w in IDS])
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        return sol

    def escorregamento_por_descoordenacao(self, vx: float, vy: float, omega: float,
                                          erro_beta_deg: float) -> float:
        """Arrasto lateral induzido por erro de calibração de UM servo [m/s].

        As quatro rodas direcionais formam um sistema SOBRE-RESTRITO: só existe
        solução sem escorregamento se as quatro normais convergirem no mesmo
        ICR. Um erro de calibração em um único servo força arrasto — este é o
        critério que define a tolerância de montagem dos servos 4WS.
        """
        cmd = self.inversa(vx, vy, omega, modo="ackermann")
        angulos = dict(cmd.angulos)
        angulos["FL"] += np.radians(erro_beta_deg)
        cmd_erro = ComandoRodas(angulos, cmd.velocidades, cmd.rpm, cmd.icr, cmd.modo, cmd.saturado)
        return float(np.max(np.abs(self.residuo_deslizamento(cmd_erro, vx, vy, omega))))


# =============================================================================
# 2. CLASSIFICAÇÃO DE SIEGWART (verificação numérica)
# =============================================================================
def classificar_siegwart(betas: Optional[Dict[str, float]] = None,
                         entre_eixos: float = None, bitola: float = None,
                         coordenado: bool = True) -> Dict[str, object]:
    """Calcula δm, δs e δM pelos postos das matrizes de restrição de Siegwart.

    O posto de C1s depende da configuração de esterçamento avaliada:

    * `coordenado=True` (padrão): as quatro rodas apontam para um ICR comum, que
      é a única configuração admissível em operação. posto(C1s) = 2, logo
      δm = 3 − 2 = 1 e δs = 2 -> categoria "Two-Steer", δM = 3.
    * `coordenado=False`: ângulos arbitrários. O posto sobe para 3 e δm cai a 0,
      isto é, O VEÍCULO TRAVA. Esse resultado não é um detalhe acadêmico: mostra
      que as quatro direções são um sistema SOBRE-RESTRITO e que qualquer erro
      de calibração de servo transforma-se em arrasto lateral e corrente extra.
    """
    cin = Cinematica4WS(entre_eixos, bitola)
    if betas is None:
        if coordenado:
            betas = cin.inversa(0.8, 0.0, 0.6, modo="ackermann").angulos
        else:
            betas = {"FL": 0.35, "FR": -0.20, "RL": 0.10, "RR": -0.45}

    # Restrição de deslizamento da roda i, atuando sobre (vx, vy, ω):
    #   −sin(β)·vx + cos(β)·vy + [x·cos(β) + y·sin(β)]·ω = 0
    # (equivalente à forma [cos(α+β) sin(α+β) l·cos(β−α)] de Siegwart, eq. 3.13,
    #  com β medido aqui em relação ao eixo x do robô)
    linhas = []
    for wid, p in cin.pos.items():
        beta = betas[wid]
        linhas.append([-np.sin(beta), np.cos(beta),
                       p[0] * np.cos(beta) + p[1] * np.sin(beta)])
    c1s = np.array(linhas)

    posto = int(np.linalg.matrix_rank(c1s, tol=1e-6))
    delta_m = 3 - posto
    delta_s = min(posto, 2)              # Siegwart: δs <= 2 (rodas extras são redundantes)
    return {
        "C1s": c1s,
        "posto_C1s": posto,
        "delta_m": delta_m,
        "delta_s": delta_s,
        "delta_M": delta_m + delta_s,
        "holonomico": bool(delta_m == 3),
        "coordenado": coordenado,
        "categoria": _categoria(delta_m, delta_s),
    }


def _categoria(dm: int, ds: int) -> str:
    tabela = {
        (3, 0): "Omnidirecional (rodas suecas/esféricas)",
        (2, 0): "Diferencial / skid-steer",
        (2, 1): "Omni-Steer",
        (1, 1): "Triciclo",
        (1, 2): "Two-Steer (4WS com rodas padrão direcionais) — o caso deste rover",
    }
    return tabela.get((dm, ds), f"δm={dm}, δs={ds} (fora da Tabela 3.1)")


def custo_reconfiguracao(modo_origem: str, modo_destino: str) -> float:
    """Tempo para reorientar as rodas ao trocar de modo cinemático [s].

    Consequência prática de δs = 2: o rover NÃO é holonômico. Passar de
    Ackermann para caranguejo exige parar e esterçar. Esse custo precisa entrar
    no cronograma da missão — o documento original o ignorava ao afirmar
    holonomia.
    """
    if modo_origem == modo_destino:
        return 0.0
    poses = {
        "ackermann": np.zeros(4),
        "crab": np.full(4, np.radians(PARAMS.estercamento.angulo_maximo_deg)),
        "spin": np.array([1, -1, -1, 1]) * np.arctan2(PARAMS.veiculo.entre_eixos_L,
                                                      PARAMS.veiculo.bitola_W),
        "stair": np.zeros(4),
    }
    delta = float(np.max(np.abs(poses[modo_destino] - poses[modo_origem])))
    taxa = np.radians(PARAMS.estercamento.taxa_maxima_deg_s)
    return delta / taxa + 0.10        # + folga de assentamento do servo


# --------------------------------------------------------------------------
# Compatibilidade com a API anterior do simulador
# --------------------------------------------------------------------------
class Kinematics4WS(Cinematica4WS):
    """Alias histórico. `compute_inverse_kinematics` mantém a assinatura antiga."""

    def compute_inverse_kinematics(self, vx_cmd: float, vz_cmd: float,
                                   omega_cmd: float, mode: str = None):
        modo = mode or "ackermann"
        # A API antiga usava (vx = lateral, vz = longitudinal): converte.
        cmd = self.inversa(vx=vz_cmd, vy=-vx_cmd, omega=omega_cmd, modo=modo)
        return cmd.angulos, cmd.velocidades, cmd.rpm
