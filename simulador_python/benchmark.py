"""
Bateria de benchmarks científicos do Rover Frugal.

Cada benchmark isola UMA decisão de projeto e mede a consequência com o mesmo
modelo físico, mudando apenas o parâmetro em estudo:

  B1  Dimensionamento da roda .... Φ300 (legado) x Φ440 (síncrona) na escada
  B2  Aro elástico ............... com x sem, em piso plano e na escada
  B3  Estágios de suspensão ...... C-STS e elásticos, ligados e desligados
  B4  Robustez de fase ........... taxa de sucesso por fase de aproximação
  B5  Cadeia de tração ........... margem de torque e limite térmico
  B6  4WS x skid-steer ........... potência de manobra (Wong, cap. 6)

Todos os gráficos são gerados sem interface (backend Agg).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .config import P as PARAMS
from .csts import dimensionar_csts, modelo_impacto
from .geometria_escada import (PerfilEscada, PerfilMeioFio, PerfilPlano,
                               RodaRaiosCurvos, SimuladorMarcha, avaliar_robustez)
from .kinematics import Cinematica4WS, classificar_siegwart, custo_reconfiguracao
from .multibody_dynamics import (ConfiguracaoSuspensao, SimuladorSagital,
                                 gerar_excitacao, metricas)
from .powertrain import (ModeloTermicoMotor, MotorCC, OrcamentoEnergia,
                         PackBateria, missao_parquetec)
from .terramechanics import TerramecanicaWong

CORES = {"ok": "#00c853", "ruim": "#ff1744", "acento": "#00b0ff",
         "aviso": "#ffa000", "neutro": "#78909c"}


def _saida(diretorio: str) -> str:
    os.makedirs(diretorio, exist_ok=True)
    return diretorio


def rodar_cenario(cfg: ConfiguracaoSuspensao, terreno, velocidade: float,
                  distancia: float = 2.2, x_inicial: float = -0.8,
                  degraus_alvo: Optional[int] = 4) -> Dict:
    """Gera a excitação COERENTE com a configuração e integra a dinâmica."""
    exc = gerar_excitacao(terreno=terreno, com_aro=cfg.com_aro,
                          x_inicial=x_inicial, degraus_alvo=degraus_alvo)
    sim = SimuladorSagital(cfg)
    dt = sim.passo_estavel()
    for tentativa in range(3):
        hist = sim.simular(exc, velocidade, distancia, dt=dt)
        m = metricas(hist)
        if not m.get("divergiu"):
            return {"excitacao": exc, "hist": hist, "metricas": m, "dt": dt}
        dt /= 4.0
    return {"excitacao": exc, "hist": hist, "metricas": m, "dt": dt}


# =============================================================================
# B1 — DIMENSIONAMENTO DA RODA
# =============================================================================
def b1_dimensionamento_roda(saida: str) -> Dict:
    esc = PARAMS.ambiente.escada
    candidatos = [("Legado Φ300 (R1)", 0.150, 0.045), ("Adotado Φ440 (R2)", 0.220, 0.070)]
    resultados = {}
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.2))
    for ax, (nome, r, rc) in zip(axs, candidatos):
        roda = RodaRaiosCurvos(num_raios=3, raio_max=r, raio_cubo=rc)
        escada = PerfilEscada(espelho=esc.espelho_E, piso=esc.piso_P, num_degraus=6)
        sim = SimuladorMarcha(roda, escada)
        res = sim.simular(x_inicial=-0.8, degraus_alvo=4)
        resultados[nome] = res

        poli = escada.poligonal()
        ax.plot(poli[:, 0], poli[:, 1], color="#455a64", lw=2)
        ax.fill_between(poli[:, 0], poli[:, 1], -0.3, color="#37474f", alpha=0.35)
        ax.plot(res.trajetoria_cubo[:, 0], res.trajetoria_cubo[:, 1],
                color=CORES["ok"] if res.sucesso else CORES["ruim"], lw=2.0,
                label="trajetória do cubo")
        for e in res.eventos:
            ax.plot(*e.contato_novo, "o", ms=4,
                    color={"nariz": CORES["acento"], "piso": CORES["neutro"],
                           "espelho": CORES["ruim"]}[e.tipo])
        alcance = 2 * r * np.sin(np.pi / 3)
        ax.set_title(f"{nome}\nalcance {alcance*1000:.0f} mm / passo exigido "
                     f"{esc.passo_D*1000:.0f} mm — "
                     f"{'ESCALA' if res.sucesso else 'FALHA'}", fontsize=10)
        ax.set_xlabel("avanço x [m]"); ax.set_ylabel("cota y [m]")
        ax.set_xlim(-0.95, 2.0); ax.set_ylim(-0.25, 1.15)
        ax.set_aspect("equal"); ax.grid(alpha=0.25); ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("B1 — Condição de marcha síncrona: D ≤ 2·r_max·sin(π/N)\n"
                 "azul = contato em nariz de degrau · cinza = contato em piso · "
                 "vermelho = apoio na face do espelho (escorrega)",
                 fontweight="bold", fontsize=11)
    fig.tight_layout()
    caminho = os.path.join(saida, "b1_dimensionamento_roda.png")
    fig.savefig(caminho, dpi=150); plt.close(fig)
    return {"resultados": resultados, "figura": caminho}


# =============================================================================
# B2 / B3 — ARO ELÁSTICO E ESTÁGIOS DE SUSPENSÃO
# =============================================================================
def b2_b3_suspensao(saida: str) -> Dict:
    cenarios = {
        "Piso plano 0,9 m/s": dict(terreno=PerfilPlano(), velocidade=0.9,
                                   x_inicial=0.0, degraus_alvo=None),
        "Escada 170x300 a 0,25 m/s": dict(terreno=PerfilEscada(num_degraus=6),
                                          velocidade=PARAMS.cinematica.velocidade_escada,
                                          x_inicial=-0.8, degraus_alvo=4),
    }
    configs = [
        ConfiguracaoSuspensao(com_csts=True, com_elasticos=True, com_aro=True),
        ConfiguracaoSuspensao(com_csts=True, com_elasticos=True, com_aro=False),
        ConfiguracaoSuspensao(com_csts=True, com_elasticos=False, com_aro=True),
        ConfiguracaoSuspensao(com_csts=False, com_elasticos=True, com_aro=True),
        ConfiguracaoSuspensao(com_csts=False, com_elasticos=False, com_aro=False),
    ]
    tabela: Dict[str, Dict[str, Dict[str, float]]] = {}
    guardados = {}
    for nome, kw in cenarios.items():
        tabela[nome] = {}
        for cfg in configs:
            r = rodar_cenario(cfg, **kw)
            tabela[nome][cfg.rotulo()] = r["metricas"]
            if cfg.com_csts and cfg.com_elasticos and cfg.com_aro:
                guardados[nome] = r

    fig, axs = plt.subplots(2, 2, figsize=(13, 8))
    for col, (nome, r) in enumerate(guardados.items()):
        h = r["hist"]
        axs[0, col].plot(r["excitacao"].x, r["excitacao"].y, color=CORES["acento"], lw=1.6)
        axs[0, col].set_title(f"{nome}\nexcitação de base y(x) do cubo", fontsize=10)
        axs[0, col].set_xlabel("x [m]"); axs[0, col].set_ylabel("y [m]"); axs[0, col].grid(alpha=0.25)

        axs[1, col].plot(h["t"], h["a_carga_vert"], color=CORES["ok"], lw=1.0,
                         label="vertical")
        axs[1, col].plot(h["t"], h["a_carga_long"], color=CORES["aviso"], lw=1.0,
                         label="longitudinal")
        axs[1, col].axhline(PARAMS.controle.limite_choque_carga_g, ls="--",
                            color=CORES["ruim"], lw=1.0, label="limite 2,0 g")
        axs[1, col].axhline(-PARAMS.controle.limite_choque_carga_g, ls="--",
                            color=CORES["ruim"], lw=1.0)
        axs[1, col].set_xlabel("t [s]"); axs[1, col].set_ylabel("aceleração na carga [g]")
        axs[1, col].grid(alpha=0.25); axs[1, col].legend(fontsize=8)
    fig.suptitle("B2/B3 — Aceleração transmitida ao notebook (configuração completa)",
                 fontweight="bold")
    fig.tight_layout()
    caminho = os.path.join(saida, "b2_b3_suspensao.png")
    fig.savefig(caminho, dpi=150); plt.close(fig)
    return {"tabela": tabela, "figura": caminho}


# =============================================================================
# B4 — ROBUSTEZ DE FASE
# =============================================================================
def b4_robustez(saida: str, raios_mm: Optional[List[float]] = None) -> Dict:
    raios_mm = raios_mm or [150, 180, 190, 200, 210, 220, 230, 240]
    esc = PARAMS.ambiente.escada
    casos = [("referência 170x300", esc.espelho_E, esc.piso_P),
             ("pior caso NBR 180x320", 0.180, 0.320)]
    dados = {}
    fig, ax = plt.subplots(figsize=(9, 5))
    for nome, E, Pp in casos:
        taxas = []
        for r in raios_mm:
            rb = avaliar_robustez(3, r * 1e-3, E, Pp, num_fases=10, degraus_alvo=3)
            taxas.append(rb.taxa_sucesso * 100.0)
            dados[(nome, r)] = rb
        ax.plot(raios_mm, taxas, "o-", lw=2, label=nome)
    ax.axvline(PARAMS.roda.raio_max * 1000, ls="--", color=CORES["ok"],
               label=f"adotado Φ{2*PARAMS.roda.raio_max*1000:.0f} mm")
    ax.axvline(150, ls=":", color=CORES["ruim"], label="legado Φ300 mm")
    ax.set_xlabel("raio máximo da roda r_max [mm]")
    ax.set_ylabel("fases de aproximação que escalam [%]")
    ax.set_title("B4 — Robustez de fase: o rover não escolhe onde encontra o 1º degrau",
                 fontweight="bold", fontsize=11)
    ax.grid(alpha=0.25); ax.legend(fontsize=9); ax.set_ylim(-5, 105)
    fig.tight_layout()
    caminho = os.path.join(saida, "b4_robustez_fase.png")
    fig.savefig(caminho, dpi=150); plt.close(fig)
    return {"dados": dados, "figura": caminho}


# =============================================================================
# B5 — CADEIA DE TRAÇÃO
# =============================================================================
def b5_tracao(saida: str) -> Dict:
    motor, termico = MotorCC(), ModeloTermicoMotor()
    orc = OrcamentoEnergia()
    curva = motor.curva()
    missao = orc.avaliar_missao(missao_parquetec())
    autonomia = orc.autonomia_ciclo_misto()

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    axs[0].plot(curva["rpm"], curva["torque"], color=CORES["acento"], lw=2)
    axs[0].axhline(PARAMS.csts.torque_projeto, ls="--", color=CORES["ruim"],
                   label=f"pico exigido na escada ({PARAMS.csts.torque_projeto:.1f} N·m)")
    axs[0].set_xlabel("rotação de saída [rpm]"); axs[0].set_ylabel("torque [N·m]")
    axs[0].set_title(f"Curva do motorredutor 1:{motor.reducao:.0f}", fontsize=10)
    axs[0].grid(alpha=0.25); axs[0].legend(fontsize=8)

    ax2 = axs[1]
    ax2.plot(curva["rpm"], curva["rendimento"] * 100, color=CORES["ok"], lw=2)
    ax2.set_xlabel("rotação de saída [rpm]"); ax2.set_ylabel("rendimento [%]")
    ax2.set_title("Rendimento: só 11% no regime de escada", fontsize=10)
    ax2.grid(alpha=0.25)

    correntes = np.linspace(2, 15, 120)
    limites = [termico.tempo_limite(i) for i in correntes]
    limites = [min(l, 600) for l in limites]
    axs[2].plot(correntes, limites, color=CORES["aviso"], lw=2)
    axs[2].axhline(11.2, ls="--", color=CORES["ok"], label="1 lance de 8 degraus (11 s)")
    axs[2].axvline(termico.corrente_continua_admissivel(), ls=":", color=CORES["neutro"],
                   label=f"contínua admissível ({termico.corrente_continua_admissivel():.1f} A)")
    axs[2].set_xlabel("corrente por motor [A]"); axs[2].set_ylabel("tempo até 115 °C [s]")
    axs[2].set_title("Limite térmico do enrolamento", fontsize=10)
    axs[2].grid(alpha=0.25); axs[2].legend(fontsize=8)

    fig.suptitle("B5 — Cadeia de tração: torque, rendimento e limite térmico",
                 fontweight="bold")
    fig.tight_layout()
    caminho = os.path.join(saida, "b5_tracao.png")
    fig.savefig(caminho, dpi=150); plt.close(fig)
    return {"missao": missao, "autonomia": autonomia, "figura": caminho,
            "corrente_continua": termico.corrente_continua_admissivel(),
            "tempo_limite_escada": termico.tempo_limite(
                missao["corrente_pico"] / PARAMS.powertrain.num_motores)}


# =============================================================================
# B6 — 4WS x SKID-STEER
# =============================================================================
def b6_manobra(saida: str) -> Dict:
    terra = TerramecanicaWong()
    raios = np.linspace(0.4, 4.0, 60)
    comp = [terra.comparar_com_skid_steer(0.8, float(r)) for r in raios]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(raios, [c["potencia_4ws_w"] for c in comp], lw=2, color=CORES["ok"],
            label="4WS coordenado (rolamento puro)")
    ax.plot(raios, [c["potencia_skid_w"] for c in comp], lw=2, color=CORES["ruim"],
            label="skid-steer (arrasto lateral, Wong cap. 6)")
    ax.set_xlabel("raio de curva [m]"); ax.set_ylabel("potência de manobra [W]")
    ax.set_title("B6 — Custo energético da manobra a 0,8 m/s", fontweight="bold", fontsize=11)
    ax.grid(alpha=0.25); ax.legend()
    fig.tight_layout()
    caminho = os.path.join(saida, "b6_manobra.png")
    fig.savefig(caminho, dpi=150); plt.close(fig)

    cin = Cinematica4WS()
    erros = {e: cin.escorregamento_por_descoordenacao(1.0, 0.0, 0.4, e)
             for e in (0.5, 1.0, 2.0, 5.0)}
    return {"comparacao": comp[len(comp) // 3], "figura": caminho,
            "siegwart": classificar_siegwart(),
            "siegwart_descoordenado": classificar_siegwart(coordenado=False),
            "erros_servo": erros,
            "custo_reconfiguracao": {m: custo_reconfiguracao("ackermann", m)
                                     for m in ("crab", "spin", "stair")}}


# =============================================================================
# EXECUÇÃO COMPLETA
# =============================================================================
def executar_tudo(diretorio: str = "resultados", verboso: bool = True) -> Dict:
    saida = _saida(diretorio)
    resultados = {}
    passos = [("B1 dimensionamento da roda", b1_dimensionamento_roda),
              ("B2/B3 suspensão", b2_b3_suspensao),
              ("B4 robustez de fase", b4_robustez),
              ("B5 cadeia de tração", b5_tracao),
              ("B6 manobra 4WS", b6_manobra)]
    for nome, fn in passos:
        if verboso:
            print(f"  ... {nome}")
        resultados[nome.split()[0]] = fn(saida)

    espiral = dimensionar_csts(PARAMS.csts.torque_projeto,
                               PARAMS.csts.deflexao_projeto_deg,
                               PARAMS.csts.material,
                               raio_externo=PARAMS.csts.raio_externo_espiral)
    resultados["espiral"] = espiral
    resultados["impacto"] = modelo_impacto(
        resultados["B1"]["resultados"]["Adotado Φ440 (R2)"].queda_maxima, espiral)
    return resultados


def run_comparative_benchmark(output_image_path: str = "resultados") -> str:
    """Compatibilidade com a CLI anterior (`--benchmark`)."""
    diretorio = (output_image_path if os.path.isdir(output_image_path)
                 or not output_image_path.endswith(".png")
                 else os.path.dirname(output_image_path) or "resultados")
    print("=" * 72)
    print("  BATERIA DE BENCHMARKS — ROVER FRUGAL 4WD/4WS")
    print("=" * 72)
    res = executar_tudo(diretorio)
    print(f"\n[OK] Figuras geradas em {os.path.abspath(diretorio)}")
    return diretorio
