"""
Dinâmica multicorpo do rover no plano sagital.

MUDANÇA DE MÉTODO EM RELAÇÃO À VERSÃO ANTERIOR
----------------------------------------------
O simulador antigo produzia a "redução de choque do C-STS" multiplicando o pico
por 0,45 quando a suspensão estava ligada e por 1,00 quando desligada. O
resultado do benchmark era, portanto, uma consequência aritmética do próprio
fator — não uma previsão física.

Aqui a cadeia causal é fechada de ponta a ponta:

  geometria da roda + perfil do degrau
        -> `geometria_escada.SimuladorMarcha` devolve a trajetória REAL do cubo
        -> essa trajetória vira a EXCITAÇÃO DE BASE y(x) de cada eixo
        -> modelo de meio-veículo (bounce + arfagem + massas não suspensas)
           filtra a excitação através do aro elástico e dos elásticos
        -> pêndulo da caixa filtra o que chega ao notebook
        -> a aceleração da carga é INTEGRADA, não postulada.

Ligar ou desligar um estágio de suspensão muda apenas a rigidez correspondente;
o ganho aparece (ou não) por conta própria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

from .config import P as PARAMS
from .csts import DinamicaCSTS, EspiralCSTS, dimensionar_csts
from .geometria_escada import (PerfilEscada, PerfilMeioFio, PerfilPlano,
                               RodaRaiosCurvos, SimuladorMarcha)
from .terramechanics import TerramecanicaWong

G = 9.80665


# =============================================================================
# 1. EXCITAÇÃO DE BASE A PARTIR DA MARCHA REAL
# =============================================================================
@dataclass
class PerfilExcitacao:
    """Cota do cubo em função do avanço, y(x), extraída da marcha geométrica."""

    x: np.ndarray
    y: np.ndarray
    sucesso: bool
    motivo: str
    queda_maxima: float
    torque_pico: float

    def __call__(self, xq: float | np.ndarray):
        return np.interp(xq, self.x, self.y, left=self.y[0], right=self.y[-1])

    @property
    def ripple(self) -> float:
        a, b = np.polyfit(self.x, self.y, 1)
        r = self.y - (a * self.x + b)
        return float(r.max() - r.min())


def gerar_excitacao(terreno=None, roda: Optional[RodaRaiosCurvos] = None,
                    com_aro: bool = True, x_inicial: float = -0.8,
                    degraus_alvo: Optional[int] = 4) -> PerfilExcitacao:
    """Roda a marcha geométrica e devolve y(x) do cubo.

    Com `com_aro=True` o aro elástico fecha a superfície de rolamento: em trecho
    plano o cubo anda na cota constante r_max (é uma roda convencional). Sem aro,
    vale a trajetória crua da roda de raios — que é o que expõe o ripple de
    r_max·(1 − cos(π/N)).
    """
    roda = roda or RodaRaiosCurvos()
    terreno = terreno if terreno is not None else PerfilEscada(num_degraus=6)
    sim = SimuladorMarcha(roda, terreno)
    res = sim.simular(x_inicial=x_inicial, degraus_alvo=degraus_alvo)

    x = res.trajetoria_cubo[:, 0]
    y = res.trajetoria_cubo[:, 1]
    ordem = np.argsort(x)
    x, y = x[ordem], y[ordem]
    x, indices = np.unique(x, return_index=True)
    y = y[indices]

    if com_aro:
        # Modelo do aro elástico: em superfície contínua ele sustenta o veículo a
        # r_max menos a deflexão estática (F/k). A trajetória dos raios só
        # prevalece onde ela é MAIOR que esse piso — isto é, quando a ponta do
        # raio está apoiada numa quina e o aro colapsou localmente.
        carga_roda = PARAMS.veiculo.peso_total_N / 4.0
        deflexao_estatica = min(carga_roda / PARAMS.aro_elastico.rigidez_radial,
                                PARAMS.aro_elastico.curso_colapso)
        piso = np.asarray(terreno.altura(x)) + roda.raio_max - deflexao_estatica
        y = np.maximum(y, piso)

    return PerfilExcitacao(x=x, y=y, sucesso=res.sucesso, motivo=res.motivo,
                           queda_maxima=res.queda_maxima, torque_pico=res.torque_pico)


# =============================================================================
# 2. MODELO DE MEIO-VEÍCULO COM CARGA PENDULAR
# =============================================================================
@dataclass
class ConfiguracaoSuspensao:
    com_csts: bool = True
    com_elasticos: bool = True
    com_aro: bool = True
    rigidez_rigida: float = 1.0e5      # N/m usada quando um estágio é desligado

    def k_elasticos(self) -> float:
        return (PARAMS.suspensao_elastica.rigidez_por_roda if self.com_elasticos
                else self.rigidez_rigida)

    def c_elasticos(self) -> float:
        return (PARAMS.suspensao_elastica.amortecimento_por_roda if self.com_elasticos
                else 5.0)

    def k_aro(self) -> float:
        return PARAMS.aro_elastico.rigidez_radial if self.com_aro else 5.0e4

    def rotulo(self) -> str:
        partes = []
        partes.append("aro" if self.com_aro else "sem aro")
        partes.append("elásticos" if self.com_elasticos else "sem elásticos")
        partes.append("C-STS" if self.com_csts else "cubo rígido")
        return " + ".join(partes)


class SimuladorSagital:
    """Meio-veículo: bounce, arfagem, 2 massas não suspensas e carga pendular."""

    def __init__(self, config: Optional[ConfiguracaoSuspensao] = None,
                 espiral: Optional[EspiralCSTS] = None):
        self.cfg = config or ConfiguracaoSuspensao()
        self.espiral = espiral or dimensionar_csts(
            torque_projeto=PARAMS.csts.torque_projeto,
            deflexao_projeto_deg=PARAMS.csts.deflexao_projeto_deg,
            material=PARAMS.csts.material,
            raio_externo=PARAMS.csts.raio_externo_espiral,
        )

        self.m_carga = PARAMS.massas.carga_util_nominal
        self.m_suspensa = PARAMS.massas.massa_seca - PARAMS.massas.rodas_conjunto - self.m_carga * 0
        self.m_nao_suspensa = PARAMS.massas.rodas_conjunto / 2.0     # por eixo (2 rodas)
        self.L = PARAMS.veiculo.entre_eixos_L
        self.lf = self.lr = self.L / 2.0
        self.inercia_arfagem = self.m_suspensa * (self.L ** 2) / 12.0 * 1.6
        self.braco_pendulo = PARAMS.veiculo.braco_pendular
        self.amort_pendulo = PARAMS.veiculo.amortecimento_pendular

        self.terramecanica = TerramecanicaWong()
        self.csts = {lado: DinamicaCSTS(self.espiral, ativo=self.cfg.com_csts)
                     for lado in ("dianteiro", "traseiro")}
        self.reset()

    # ------------------------------------------------------------------
    def reset(self) -> None:
        r = PARAMS.roda.raio_max
        self.t = 0.0
        self.x = 0.0
        self.v = 0.0
        self.z_s = r + PARAMS.veiculo.altura_cg_chassi
        self.dz_s = 0.0
        self.theta = 0.0
        self.dtheta = 0.0
        self.z_uf = r
        self.dz_uf = 0.0
        self.z_ur = r
        self.dz_ur = 0.0
        self.phi = 0.0
        self.dphi = 0.0
        self.hist: Dict[str, List[float]] = {
            k: [] for k in ("t", "x", "v", "z_s", "theta", "z_uf", "z_ur", "phi",
                            "a_carga_vert", "a_carga_long", "fz_f", "fz_r",
                            "deflexao_csts", "energia_csts", "torque_roda")
        }

    # ------------------------------------------------------------------
    def passo(self, excitacao: PerfilExcitacao, velocidade_alvo: float, dt: float) -> None:
        # --- longitudinal com complacência torsional -----------------------
        self.v += (velocidade_alvo - self.v) * min(1.0, dt * 4.0)
        self.x += self.v * dt

        r = PARAMS.roda.raio_max
        omega_motor = self.v / r
        torque_resistente = excitacao.torque_pico * 0.0   # atualizado abaixo
        # Torque resistente instantâneo: braço horizontal do contato (da marcha)
        inclinacao_local = self._inclinacao_local(excitacao, self.x)
        torque_resistente = (self.terramecanica.peso / 2.0) * r * np.sin(inclinacao_local)
        t_transmitido = self.csts["dianteiro"].passo(omega_motor, torque_resistente, dt)
        self.csts["traseiro"].passo(omega_motor, torque_resistente, dt)

        # Aceleração longitudinal da carga = variação da força trativa efetiva
        a_long = (t_transmitido / r - torque_resistente / r) / max(PARAMS.massas.massa_total, 1e-6)

        # --- excitação de base dos dois eixos ------------------------------
        y_f = float(excitacao(self.x + self.lf))
        y_r = float(excitacao(self.x - self.lr))

        # --- forças do aro elástico (contato) ------------------------------
        k_aro, k_sus, c_sus = self.cfg.k_aro(), self.cfg.k_elasticos(), self.cfg.c_elasticos()
        f_contato_f = max(0.0, k_aro * (y_f - self.z_uf))
        f_contato_r = max(0.0, k_aro * (y_r - self.z_ur))

        # --- forças da suspensão elástica ----------------------------------
        z_s_f = self.z_s - self.lf * np.sin(self.theta) - PARAMS.veiculo.altura_cg_chassi
        z_s_r = self.z_s + self.lr * np.sin(self.theta) - PARAMS.veiculo.altura_cg_chassi
        dz_s_f = self.dz_s - self.lf * self.dtheta
        dz_s_r = self.dz_s + self.lr * self.dtheta

        curso = PARAMS.suspensao_elastica.curso_maximo
        def forca_susp(z_u, z_sx, dz_u, dz_sx):
            defl = z_u - z_sx
            f = k_sus * defl + c_sus * (dz_u - dz_sx)
            if abs(defl) > curso:              # batente mecânico de fim de curso
                f += 2.0e4 * (abs(defl) - curso) * np.sign(defl)
            return f

        f_sus_f = forca_susp(self.z_uf, z_s_f, self.dz_uf, dz_s_f)
        f_sus_r = forca_susp(self.z_ur, z_s_r, self.dz_ur, dz_s_r)

        # --- massas não suspensas -------------------------------------------
        ddz_uf = (f_contato_f - f_sus_f) / self.m_nao_suspensa - G
        ddz_ur = (f_contato_r - f_sus_r) / self.m_nao_suspensa - G
        self.dz_uf += ddz_uf * dt
        self.dz_ur += ddz_ur * dt
        self.z_uf += self.dz_uf * dt
        self.z_ur += self.dz_ur * dt

        # --- massa suspensa (bounce + arfagem) ------------------------------
        m_total_susp = self.m_suspensa + self.m_carga
        ddz_s = (f_sus_f + f_sus_r) / m_total_susp - G
        ddtheta = (f_sus_r * self.lr - f_sus_f * self.lf) / self.inercia_arfagem
        self.dz_s += ddz_s * dt
        self.z_s += self.dz_s * dt
        self.dtheta += ddtheta * dt
        self.theta += self.dtheta * dt

        # --- pêndulo da caixa organizadora ----------------------------------
        ddphi = (-(G / self.braco_pendulo) * np.sin(self.phi - self.theta)
                 - self.amort_pendulo * (self.dphi - self.dtheta)
                 - a_long / self.braco_pendulo)
        self.dphi += ddphi * dt
        self.phi += self.dphi * dt

        # --- aceleração sentida pelo notebook -------------------------------
        a_vert = ddz_s + self.braco_pendulo * ddphi * np.sin(self.phi)
        a_long_carga = a_long + self.braco_pendulo * ddphi * np.cos(self.phi)

        self.t += dt
        h = self.hist
        h["t"].append(self.t); h["x"].append(self.x); h["v"].append(self.v)
        h["z_s"].append(self.z_s); h["theta"].append(np.degrees(self.theta))
        h["z_uf"].append(self.z_uf); h["z_ur"].append(self.z_ur)
        h["phi"].append(np.degrees(self.phi))
        h["a_carga_vert"].append(a_vert / G)
        h["a_carga_long"].append(a_long_carga / G)
        h["fz_f"].append(f_contato_f); h["fz_r"].append(f_contato_r)
        h["deflexao_csts"].append(np.degrees(self.csts["dianteiro"].deflexao))
        h["energia_csts"].append(self.csts["dianteiro"].energia)
        h["torque_roda"].append(t_transmitido)

    # ------------------------------------------------------------------
    @staticmethod
    def _inclinacao_local(exc: PerfilExcitacao, x: float, janela: float = 0.15) -> float:
        y1 = float(exc(x - janela / 2.0))
        y2 = float(exc(x + janela / 2.0))
        return float(np.arctan2(y2 - y1, janela))

    def passo_estavel(self) -> float:
        """Passo de integração pela frequência natural mais alta do sistema.

        Euler semi-implícito é estável para ω·dt < 2; adota-se ω·dt <= 0,10 para
        manter também a precisão. Sem isto, as configurações "sem suspensão"
        (rigidez de 1e5 N/m) divergem e produzem números sem sentido físico.
        """
        k_max = max(self.cfg.k_aro(), self.cfg.k_elasticos())
        m_min = min(self.m_nao_suspensa, self.m_suspensa + self.m_carga)
        omega = np.sqrt(2.0 * k_max / m_min)
        return float(min(5.0e-4, 0.10 / omega))

    def simular(self, excitacao: PerfilExcitacao, velocidade: float,
                distancia: float, dt: Optional[float] = None) -> Dict[str, np.ndarray]:
        self.reset()
        self.x = float(excitacao.x[0])
        dt = self.passo_estavel() if dt is None else dt
        passos = int(distancia / max(velocidade, 1e-3) / dt)
        self.divergiu = False
        for _ in range(passos):
            self.passo(excitacao, velocidade, dt)
            if not np.isfinite(self.z_s) or abs(self.theta) > np.pi or abs(self.z_s) > 5.0:
                self.divergiu = True
                break
            if self.x > excitacao.x[-1]:
                break
        saida = {k: np.array(v) for k, v in self.hist.items()}
        saida["_divergiu"] = np.array([self.divergiu])
        saida["_dt"] = np.array([dt])
        return saida


# =============================================================================
# 3. MÉTRICAS
# =============================================================================
def metricas(hist: Dict[str, np.ndarray]) -> Dict[str, float]:
    """Métricas de conforto/integridade da carga a partir de uma corrida."""
    if bool(hist.get("_divergiu", np.array([False]))[0]):
        return {"pico_vertical_g": float("inf"), "rms_vertical_g": float("inf"),
                "pico_longitudinal_g": float("inf"), "pico_arfagem_deg": float("inf"),
                "energia_csts_max_j": 0.0, "deflexao_csts_max_deg": 0.0, "divergiu": True}
    av, al = hist["a_carga_vert"], hist["a_carga_long"]
    n = max(1, len(av) // 10)     # descarta o transiente inicial de assentamento
    av, al = av[n:], al[n:]
    if len(av) == 0:
        return {"pico_vertical_g": 0.0, "rms_vertical_g": 0.0, "pico_longitudinal_g": 0.0,
                "pico_arfagem_deg": 0.0, "energia_csts_max_j": 0.0, "deflexao_csts_max_deg": 0.0}
    return {
        "pico_vertical_g": float(np.max(np.abs(av))),
        "rms_vertical_g": float(np.sqrt(np.mean(av ** 2))),
        "pico_longitudinal_g": float(np.max(np.abs(al))),
        "pico_arfagem_deg": float(np.max(np.abs(hist["theta"][n:]))),
        "energia_csts_max_j": float(np.max(hist["energia_csts"][n:])),
        "deflexao_csts_max_deg": float(np.max(np.abs(hist["deflexao_csts"][n:]))),
        "divergiu": False,
    }


# Alias histórico
RoverMultibodySimulator = SimuladorSagital
