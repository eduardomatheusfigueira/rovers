"""
Suspensão Complacente Torsional (C-STS) — dimensionamento e dinâmica de impacto.

Jeong & Kim (2025) publicam uma mola espiral plana com kt ~ 0,55 N·m/rad para um
robô de bancada. Copiar esse valor para o Rover Frugal seria um erro grosseiro de
escala: com r_max = 0,22 m e torque de acionamento de pico ~4,8 N·m, a deflexão
seria de 4,8/0,55 = 8,7 rad (500°) — a mola enrolaria completamente e bateria no
batente já no primeiro degrau.

Este módulo faz o que o artigo não faz por nós: transporta o conceito por
SEMELHANÇA DIMENSIONAL. A rigidez é derivada do torque de projeto e da deflexão
admissível, e a geometria da espiral (b, t, L, número de voltas) é resolvida a
partir da rigidez, verificando tensão de flexão e caber dentro do cubo.

    kt = E · b · t³ / (12 · L)          rigidez da viga espiral plana
    σ  = 6 · M / (b · t²)               tensão de flexão máxima na lâmina
    L  ≈ π · n · (r_i + r_o)            comprimento desenrolado de n voltas
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .config import P as PARAMS

# Propriedades de materiais FDM (valores de projeto conservadores, corpo de prova XY)
MATERIAIS = {
    "PLA":  {"E": 3.5e9, "sigma_escoamento": 55e6, "densidade": 1240.0},
    "PETG": {"E": 2.1e9, "sigma_escoamento": 50e6, "densidade": 1270.0},
    "ABS":  {"E": 2.0e9, "sigma_escoamento": 40e6, "densidade": 1040.0},
}

#: Correção empírica: a lâmina impressa em FDM é mais flexível que a viga ideal
#: (aderência parcial entre filetes). Razão kt_experimental/kt_teórico medida por
#: Jeong & Kim (2025) nas três variantes de espessura.
FATOR_FDM = PARAMS.csts.fator_correcao_empirico


@dataclass
class EspiralCSTS:
    """Geometria e propriedades resolvidas de uma mola espiral plana."""

    material: str
    largura_b: float
    espessura_t: float
    comprimento_L: float
    num_voltas: float
    raio_interno: float
    raio_externo: float
    kt_teorico: float
    kt_efetivo: float
    torque_projeto: float
    deflexao_projeto: float
    tensao_maxima: float
    fator_seguranca: float
    cabe_no_cubo: bool
    massa: float

    def energia_armazenada(self, deflexao: float | np.ndarray):
        """U = ½·kt·Δθ² [J]."""
        return 0.5 * self.kt_efetivo * np.asarray(deflexao) ** 2

    def rigidez_linear_equivalente(self, raio_contato: float) -> float:
        """Rigidez vista pelo ponto de contato: k = kt / r²  [N/m]."""
        return self.kt_efetivo / max(raio_contato, 1e-6) ** 2

    def resumo(self) -> str:
        return (
            f"C-STS em {self.material}: b={self.largura_b*1000:.1f} mm, "
            f"t={self.espessura_t*1000:.2f} mm, L={self.comprimento_L*1000:.0f} mm, "
            f"{self.num_voltas:.1f} voltas (r {self.raio_interno*1000:.0f}→"
            f"{self.raio_externo*1000:.0f} mm)\n"
            f"  kt teórico / efetivo ..... {self.kt_teorico:.2f} / {self.kt_efetivo:.2f} N·m/rad\n"
            f"  torque / deflexão projeto  {self.torque_projeto:.2f} N·m @ "
            f"{np.degrees(self.deflexao_projeto):.1f}°\n"
            f"  tensão de flexão ......... {self.tensao_maxima/1e6:.1f} MPa "
            f"(FS = {self.fator_seguranca:.1f})\n"
            f"  energia no pico .......... {self.energia_armazenada(self.deflexao_projeto):.2f} J\n"
            f"  massa .................... {self.massa*1000:.0f} g   "
            f"cabe no cubo: {'sim' if self.cabe_no_cubo else 'NÃO'}"
        )


def dimensionar_csts(
    torque_projeto: float,
    deflexao_projeto_deg: float = 30.0,
    material: str = "PETG",
    raio_interno: float = 0.020,
    raio_externo: Optional[float] = None,
    largura_b: float = 0.030,
    folga_entre_voltas: float = 0.002,
    fator_seguranca_minimo: float = 2.0,
) -> EspiralCSTS:
    """Resolve a geometria da espiral a partir do torque e da deflexão de projeto.

    Procedimento:
      1. kt_efetivo = T / Δθ  (definição de rigidez de projeto).
      2. kt_teorico = kt_efetivo / FATOR_FDM  (compensa a perda de rigidez do FDM).
      3. Para cada número inteiro de voltas n, calcula L e resolve t pela
         equação de rigidez; aceita a primeira solução que caiba no cubo e
         satisfaça o fator de segurança em flexão.
    """
    if material not in MATERIAIS:
        raise ValueError(f"Material '{material}' fora de {sorted(MATERIAIS)}")
    prop = MATERIAIS[material]
    if raio_externo is None:
        raio_externo = PARAMS.roda.raio_cubo - 0.008    # deixa a parede do cubo

    deflexao = float(np.radians(deflexao_projeto_deg))
    kt_efetivo = torque_projeto / deflexao
    kt_teorico = kt_efetivo / FATOR_FDM

    banda_radial = raio_externo - raio_interno
    melhor = None
    for n in np.arange(1.5, 8.01, 0.5):
        L = np.pi * n * (raio_interno + raio_externo)
        t = ((12.0 * kt_teorico * L) / (prop["E"] * largura_b)) ** (1.0 / 3.0)
        cabe = n * (t + folga_entre_voltas) <= banda_radial
        sigma = 6.0 * torque_projeto / (largura_b * t ** 2)
        fs = prop["sigma_escoamento"] / sigma
        if cabe and fs >= fator_seguranca_minimo:
            melhor = (n, L, t, sigma, fs, True)
            break
        if melhor is None or (not melhor[5] and cabe):
            melhor = (n, L, t, sigma, fs, cabe)

    n, L, t, sigma, fs, cabe = melhor
    volume = largura_b * t * L
    return EspiralCSTS(
        material=material, largura_b=largura_b, espessura_t=t, comprimento_L=L,
        num_voltas=float(n), raio_interno=raio_interno, raio_externo=raio_externo,
        kt_teorico=kt_teorico, kt_efetivo=kt_efetivo, torque_projeto=torque_projeto,
        deflexao_projeto=deflexao, tensao_maxima=sigma, fator_seguranca=fs,
        cabe_no_cubo=bool(cabe), massa=volume * prop["densidade"],
    )


# =============================================================================
# Modelo de impacto na transferência de raio (DCS)
# =============================================================================
@dataclass
class ResultadoImpacto:
    velocidade_impacto: float      # m/s
    aceleracao_rigida: float       # m/s² — ponta rígida direto no chassi
    aceleracao_csts: float         # m/s² — só com o estágio torsional
    aceleracao_completa: float     # m/s² — C-STS + elásticos em série
    reducao_percentual: float

    @property
    def em_g(self):
        g = 9.80665
        return (self.aceleracao_rigida / g, self.aceleracao_csts / g,
                self.aceleracao_completa / g)

    def resumo(self) -> str:
        g = 9.80665
        return (
            f"Impacto na transferência de raio (queda equivalente a "
            f"{self.velocidade_impacto:.2f} m/s):\n"
            f"  ponta rígida (sem suspensão) .......... {self.aceleracao_rigida:8.1f} m/s² "
            f"({self.aceleracao_rigida/g:5.1f} g)\n"
            f"  só C-STS (estágio 1) .................. {self.aceleracao_csts:8.1f} m/s² "
            f"({self.aceleracao_csts/g:5.1f} g)\n"
            f"  C-STS + elásticos (estágios 1+2) ...... {self.aceleracao_completa:8.1f} m/s² "
            f"({self.aceleracao_completa/g:5.1f} g)\n"
            f"  redução total ......................... {self.reducao_percentual:.1f}%"
        )


def modelo_impacto(
    queda_cubo: float,
    espiral: EspiralCSTS,
    raio_contato: float = None,
    massa_por_roda: float = None,
    rigidez_elasticos: float = None,
    rigidez_contato_rigido: float = 5.0e4,
) -> ResultadoImpacto:
    """Pico de desaceleração na transferência de raio, por modelo massa-mola.

    Uma massa m chegando a uma mola k com velocidade v sofre pico de
    desaceleração a_max = v·sqrt(k/m) (movimento harmônico simples). A queda do
    cubo entre duas transferências vem da GEOMETRIA (simulador de marcha), não
    de ajuste: `queda_cubo` é medido em `geometria_escada.SimuladorMarcha`.

    Os dois estágios agem em série, logo somam-se as flexibilidades:
        1/k_total = 1/k_csts + 1/k_elásticos
    """
    if raio_contato is None:
        raio_contato = PARAMS.roda.raio_max
    if massa_por_roda is None:
        massa_por_roda = PARAMS.massas.massa_total / 4.0
    if rigidez_elasticos is None:
        rigidez_elasticos = PARAMS.suspensao_elastica.rigidez_por_roda

    v = float(np.sqrt(2.0 * 9.80665 * max(queda_cubo, 0.0)))
    k_csts = espiral.rigidez_linear_equivalente(raio_contato)
    k_serie = 1.0 / (1.0 / k_csts + 1.0 / rigidez_elasticos)

    a_rigido = v * np.sqrt(rigidez_contato_rigido / massa_por_roda)
    a_csts = v * np.sqrt(k_csts / massa_por_roda)
    a_total = v * np.sqrt(k_serie / massa_por_roda)
    reducao = 100.0 * (1.0 - a_total / a_rigido) if a_rigido > 0 else 0.0
    return ResultadoImpacto(v, a_rigido, a_csts, a_total, reducao)


# =============================================================================
# Dinâmica torsional no tempo (para o simulador multicorpo)
# =============================================================================
class DinamicaCSTS:
    """Integra a torção do cubo: J·θ̈ = T_motor − kt·Δθ − ct·Δθ̇ − T_contato."""

    def __init__(self, espiral: Optional[EspiralCSTS] = None, ativo: bool = True):
        self.ativo = ativo
        self.espiral = espiral
        # Com o C-STS desligado a roda é SOLIDÁRIA ao eixo (acoplamento rígido),
        # não uma mola muito dura: modelar como mola de 1e5 N·m/rad exigiria
        # passo de integração de ~1e-5 s e só introduziria ruído numérico.
        self.kt = espiral.kt_efetivo if (espiral and ativo) else float("inf")
        self.ct = PARAMS.csts.amortecimento_ct if ativo else 50.0
        self.inercia = PARAMS.csts.inercia_roda
        self.limite = PARAMS.csts.deflexao_maxima_rad

        self.theta_motor = 0.0
        self.omega_motor = 0.0
        self.theta_roda = 0.0
        self.omega_roda = 0.0

    @property
    def deflexao(self) -> float:
        return self.theta_motor - self.theta_roda

    @property
    def energia(self) -> float:
        return 0.0 if not self.ativo else 0.5 * self.kt * self.deflexao ** 2

    @property
    def torque_transmitido(self) -> float:
        if not self.ativo:
            return 0.0
        d = float(np.clip(self.deflexao, -self.limite, self.limite))
        rigido = 0.0
        if abs(self.deflexao) > self.limite:      # batente mecânico de fim de curso
            rigido = 1.0e4 * (abs(self.deflexao) - self.limite) * np.sign(self.deflexao)
        return self.kt * d + self.ct * (self.omega_motor - self.omega_roda) + rigido

    def passo(self, omega_motor: float, torque_resistente: float, dt: float) -> float:
        """Avança um passo; devolve o torque transmitido à roda."""
        self.omega_motor = omega_motor
        self.theta_motor += omega_motor * dt
        if not self.ativo:
            # Acoplamento rígido: a roda segue o motor e transmite tudo.
            self.theta_roda = self.theta_motor
            self.omega_roda = omega_motor
            return torque_resistente
        t_mola = self.torque_transmitido
        alpha = (t_mola - torque_resistente) / self.inercia
        self.omega_roda += alpha * dt
        self.theta_roda += self.omega_roda * dt
        return t_mola
