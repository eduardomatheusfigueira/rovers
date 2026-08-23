"""
Cadeia de tração e orçamento de energia.

Substitui a conta de guardanapo do documento original (que usava r = 0,10 m para
a roda enquanto o resto do projeto usava 0,15 m, subestimando o torque em 50%)
por um modelo elétrico-mecânico completo:

  * Motor CC de ímã permanente com curva torque-velocidade real
    (T = Kt·(V − Ke·ω_rotor)/R_a − T_atrito), corrente e rendimento;
  * Redutor planetário com rendimento mecânico;
  * Pack de bateria com queda por resistência interna e reserva operacional;
  * Perfil de missão por trechos, integrando energia e verificando margens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .config import P as PARAMS

G = 9.80665


# =============================================================================
# 1. MOTOR + REDUTOR
# =============================================================================
@dataclass
class MotorCC:
    """Motor CC escovado com redutor planetário, no eixo de saída."""

    tensao_nominal: float = PARAMS.powertrain.motor.tensao_nominal
    kv_rpm_por_volt: float = PARAMS.powertrain.motor.kv_rpm_por_volt
    resistencia: float = PARAMS.powertrain.motor.resistencia_armadura
    corrente_vazio: float = PARAMS.powertrain.motor.corrente_vazio
    reducao: float = PARAMS.powertrain.reducao
    eficiencia_reducao: float = PARAMS.powertrain.eficiencia_reducao
    limite_corrente: float = PARAMS.powertrain.limite_corrente_driver

    @property
    def kt(self) -> float:
        """Constante de torque [N·m/A] = constante de fcem [V·s/rad]."""
        return 60.0 / (2.0 * np.pi * self.kv_rpm_por_volt)

    @property
    def corrente_stall(self) -> float:
        return self.tensao_nominal / self.resistencia

    @property
    def torque_stall_saida(self) -> float:
        return self.kt * (self.corrente_stall - self.corrente_vazio) * \
            self.reducao * self.eficiencia_reducao

    @property
    def omega_vazio_saida(self) -> float:
        return (self.kv_rpm_por_volt * self.tensao_nominal / self.reducao) * 2.0 * np.pi / 60.0

    def ponto_operacao(self, omega_saida: float, tensao: Optional[float] = None) -> Dict[str, float]:
        """Resolve o ponto de operação para uma rotação de saída imposta."""
        v = self.tensao_nominal if tensao is None else tensao
        omega_rotor = abs(omega_saida) * self.reducao
        fcem = self.kt * omega_rotor
        corrente = max(0.0, (v - fcem) / self.resistencia)
        corrente = min(corrente, self.limite_corrente)
        torque_rotor = self.kt * max(0.0, corrente - self.corrente_vazio)
        torque_saida = torque_rotor * self.reducao * self.eficiencia_reducao
        p_eletrica = v * corrente
        p_mecanica = torque_saida * abs(omega_saida)
        return {
            "omega_saida": abs(omega_saida),
            "rpm_saida": abs(omega_saida) * 60.0 / (2.0 * np.pi),
            "corrente": corrente,
            "torque_saida": torque_saida,
            "potencia_eletrica": p_eletrica,
            "potencia_mecanica": p_mecanica,
            "rendimento": p_mecanica / p_eletrica if p_eletrica > 1e-6 else 0.0,
        }

    def corrente_para_torque(self, torque_saida: float) -> float:
        """Corrente necessária para entregar um torque no eixo de saída."""
        torque_rotor = abs(torque_saida) / (self.reducao * self.eficiencia_reducao)
        return torque_rotor / self.kt + self.corrente_vazio

    def curva(self, n: int = 120) -> Dict[str, np.ndarray]:
        omega = np.linspace(1e-3, self.omega_vazio_saida, n)
        pontos = [self.ponto_operacao(w) for w in omega]
        return {
            "omega": omega,
            "rpm": np.array([p["rpm_saida"] for p in pontos]),
            "torque": np.array([p["torque_saida"] for p in pontos]),
            "corrente": np.array([p["corrente"] for p in pontos]),
            "potencia": np.array([p["potencia_mecanica"] for p in pontos]),
            "rendimento": np.array([p["rendimento"] for p in pontos]),
        }


@dataclass
class ModeloTermicoMotor:
    """Modelo térmico de 1ª ordem do enrolamento (perda ôhmica -> temperatura).

    Em escada o motor opera a ~11% de rendimento: quase toda a potência elétrica
    vira calor no enrolamento. O limite de missão não é a energia da bateria —
    é o tempo até o enrolamento atingir a temperatura de classe do esmalte.
    """

    resistencia: float = PARAMS.powertrain.motor.resistencia_armadura
    r_termica: float = 8.0          # K/W — enrolamento para o ambiente
    c_termica: float = 30.0         # J/K — capacidade térmica do enrolamento
    temp_ambiente: float = 35.0     # °C — pior caso de verão em Foz do Iguaçu
    temp_maxima: float = 115.0      # °C — classe do esmalte com margem

    @property
    def tau(self) -> float:
        return self.r_termica * self.c_termica

    def temperatura(self, corrente: float, tempo: float, temp_inicial: Optional[float] = None) -> float:
        t0 = self.temp_ambiente if temp_inicial is None else temp_inicial
        p = corrente ** 2 * self.resistencia
        regime = self.temp_ambiente + p * self.r_termica
        return regime + (t0 - regime) * np.exp(-tempo / self.tau)

    def tempo_limite(self, corrente: float, temp_inicial: Optional[float] = None) -> float:
        """Tempo até atingir `temp_maxima` nessa corrente (inf se não atinge)."""
        t0 = self.temp_ambiente if temp_inicial is None else temp_inicial
        p = corrente ** 2 * self.resistencia
        regime = self.temp_ambiente + p * self.r_termica
        if regime <= self.temp_maxima:
            return float("inf")
        return float(self.tau * np.log((regime - t0) / (regime - self.temp_maxima)))

    def corrente_continua_admissivel(self) -> float:
        """Corrente que estabiliza exatamente em `temp_maxima`."""
        p = (self.temp_maxima - self.temp_ambiente) / self.r_termica
        return float(np.sqrt(p / self.resistencia))


# =============================================================================
# 2. BATERIA
# =============================================================================
@dataclass
class PackBateria:
    serie: int = PARAMS.energia.celulas_serie
    paralelo: int = PARAMS.energia.celulas_paralelo
    capacidade_celula_ah: float = PARAMS.energia.capacidade_celula_ah
    tensao_nominal_celula: float = PARAMS.energia.tensao_nominal_celula
    tensao_cheia_celula: float = PARAMS.energia.tensao_cheia_celula
    tensao_corte_celula: float = PARAMS.energia.tensao_corte_celula
    r_interna_celula: float = PARAMS.energia.resistencia_interna_celula
    reserva: float = PARAMS.energia.reserva_operacional

    @property
    def capacidade_ah(self) -> float:
        return self.paralelo * self.capacidade_celula_ah

    @property
    def tensao_nominal(self) -> float:
        return self.serie * self.tensao_nominal_celula

    @property
    def r_interna(self) -> float:
        return self.r_interna_celula * self.serie / self.paralelo

    @property
    def energia_wh(self) -> float:
        return self.capacidade_ah * self.tensao_nominal

    @property
    def energia_util_wh(self) -> float:
        return self.energia_wh * (1.0 - self.reserva)

    def tensao_sob_carga(self, corrente: float, soc: float = 1.0) -> float:
        """Tensão nos terminais: OCV(SOC) menos a queda ôhmica interna."""
        ocv_celula = (self.tensao_corte_celula
                      + (self.tensao_cheia_celula - self.tensao_corte_celula)
                      * (0.15 + 0.85 * float(np.clip(soc, 0.0, 1.0))))
        return self.serie * ocv_celula - corrente * self.r_interna

    def taxa_c(self, corrente: float) -> float:
        return corrente / self.capacidade_ah


# =============================================================================
# 3. RESISTÊNCIAS AO MOVIMENTO E PERFIL DE MISSÃO
# =============================================================================
@dataclass
class TrechoMissao:
    nome: str
    distancia: float               # m
    inclinacao_deg: float = 0.0
    velocidade: float = 1.0        # m/s
    crr: float = PARAMS.ambiente.piso.crr_asfalto
    escada: bool = False
    torque_extra_por_roda: float = 0.0   # N·m — pico geométrico em degraus


@dataclass
class ResultadoTrecho:
    trecho: TrechoMissao
    duracao: float
    forca_total: float
    torque_por_roda: float
    corrente_total: float
    potencia_total: float
    energia_wh: float
    margem_torque: float
    tensao_terminal: float
    viavel: bool


class OrcamentoEnergia:
    """Integra um perfil de missão trecho a trecho."""

    def __init__(self, motor: Optional[MotorCC] = None, pack: Optional[PackBateria] = None,
                 massa: Optional[float] = None, raio_roda: Optional[float] = None):
        self.motor = motor or MotorCC()
        self.pack = pack or PackBateria()
        self.massa = massa if massa is not None else PARAMS.massas.massa_total
        self.raio = raio_roda if raio_roda is not None else PARAMS.roda.raio_max
        self.num_motores = PARAMS.powertrain.num_motores
        self.consumo_auxiliar = PARAMS.energia.consumo_eletronica_w

    def avaliar_trecho(self, t: TrechoMissao, soc: float = 1.0) -> ResultadoTrecho:
        peso = self.massa * G
        theta = np.radians(t.inclinacao_deg)
        f_subida = peso * np.sin(theta)
        f_rolamento = t.crr * peso * np.cos(theta)
        f_total = f_subida + f_rolamento

        torque_roda = f_total * self.raio / self.num_motores + t.torque_extra_por_roda
        omega = t.velocidade / self.raio

        op = self.motor.ponto_operacao(omega, tensao=self.pack.tensao_sob_carga(0.0, soc))
        disponivel = op["torque_saida"]
        corrente_1 = self.motor.corrente_para_torque(torque_roda)
        corrente_total = corrente_1 * self.num_motores
        tensao = self.pack.tensao_sob_carga(corrente_total, soc)
        potencia = tensao * corrente_total + self.consumo_auxiliar
        duracao = t.distancia / max(t.velocidade, 1e-3)
        energia = potencia * duracao / 3600.0
        margem = disponivel / torque_roda if torque_roda > 1e-6 else float("inf")

        return ResultadoTrecho(
            trecho=t, duracao=duracao, forca_total=f_total, torque_por_roda=torque_roda,
            corrente_total=corrente_total, potencia_total=potencia, energia_wh=energia,
            margem_torque=margem, tensao_terminal=tensao,
            viavel=bool(margem >= 1.0 and tensao >= self.pack.serie * self.pack.tensao_corte_celula),
        )

    def avaliar_missao(self, trechos: List[TrechoMissao]) -> Dict:
        resultados, energia_acum, soc = [], 0.0, 1.0
        for t in trechos:
            r = self.avaliar_trecho(t, soc=soc)
            energia_acum += r.energia_wh
            soc = max(0.0, 1.0 - energia_acum / self.pack.energia_wh)
            resultados.append(r)
        duracao = sum(r.duracao for r in resultados)
        distancia = sum(r.trecho.distancia for r in resultados)
        return {
            "trechos": resultados,
            "energia_total_wh": energia_acum,
            "duracao_total_s": duracao,
            "distancia_total_m": distancia,
            "soc_final": soc,
            "fracao_energia_util": energia_acum / self.pack.energia_util_wh,
            "margem_torque_minima": min(r.margem_torque for r in resultados),
            "corrente_pico": max(r.corrente_total for r in resultados),
            "taxa_c_pico": self.pack.taxa_c(max(r.corrente_total for r in resultados)),
            "viavel": all(r.viavel for r in resultados)
                      and energia_acum <= self.pack.energia_util_wh,
        }

    def autonomia_ciclo_misto(self, fracao_plano: float = 0.75,
                              fracao_rampa: float = 0.20,
                              fracao_escada: float = 0.05,
                              torque_extra_escada: float = 4.81) -> Dict[str, float]:
        """Autonomia em regime, por potência média ponderada do ciclo misto."""
        base = [
            (fracao_plano, TrechoMissao("plano", 100.0, 0.0, PARAMS.cinematica.velocidade_maxima * 0.8)),
            (fracao_rampa, TrechoMissao("rampa", 100.0, 8.0, PARAMS.cinematica.velocidade_maxima * 0.6)),
            (fracao_escada, TrechoMissao("escada", 100.0, PARAMS.ambiente.escada.inclinacao_deg,
                                         PARAMS.cinematica.velocidade_escada, crr=0.15,
                                         escada=True, torque_extra_por_roda=torque_extra_escada)),
        ]
        potencia_media = sum(f * self.avaliar_trecho(t).potencia_total for f, t in base)
        horas = self.pack.energia_util_wh / max(potencia_media, 1e-6)
        return {
            "potencia_media_w": potencia_media,
            "autonomia_min": horas * 60.0,
            "autonomia_h": horas,
        }


# =============================================================================
# 4. MISSÃO DE HOMOLOGAÇÃO (Parquetec)
# =============================================================================
def missao_parquetec() -> List[TrechoMissao]:
    """Perfil da missão de homologação descrita em 05_Execucao/03."""
    v = PARAMS.cinematica.velocidade_maxima * 0.8
    v_esc = PARAMS.cinematica.velocidade_escada
    inc = PARAMS.ambiente.escada.inclinacao_deg
    t_extra = 4.81
    return [
        TrechoMissao("Base -> calçada (asfalto)", 180.0, 0.0, v),
        TrechoMissao("Rampa de acessibilidade (8%)", 25.0, 4.6, v * 0.7),
        TrechoMissao("Calçada de paver", 120.0, 0.0, v, crr=0.045),
        TrechoMissao("Meio-fio + soleira", 6.0, 0.0, 0.3, crr=0.12, torque_extra_por_roda=3.0),
        TrechoMissao("Corredor interno (piso liso)", 60.0, 0.0, v * 0.6, crr=0.02),
        TrechoMissao("Embarque do notebook (parado)", 0.5, 0.0, 0.05),
        TrechoMissao("Retorno em calçada (com carga)", 150.0, 0.0, v, crr=0.045),
        TrechoMissao("Escada de 8 degraus (subida)", 2.8, inc, v_esc, crr=0.15,
                     escada=True, torque_extra_por_roda=t_extra),
        TrechoMissao("Corredor até a T.I.", 45.0, 0.0, v * 0.6, crr=0.02),
    ]
