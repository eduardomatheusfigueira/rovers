"""
Carregador de Parâmetros Mestres do Rover Frugal 4WD/4WS.

Todos os números de engenharia vivem em `00_Especificacao_Mestre/parametros_mestres.yaml`.
Este módulo:
  1. Carrega o YAML, aplica a variante ativa (ou a solicitada) e resolve os
     valores DERIVADOS (aqueles que são função de outros parâmetros).
  2. Expõe um objeto `P` (dicionário aninhado com acesso por atributo).
  3. Reexporta as constantes planas legadas (MASS_TOTAL, R_WHEEL_MAX, ...) para
     manter compatibilidade com o código existente do simulador.

Referências normativas dos valores: ver cabeçalho do YAML e
`00_Especificacao_Mestre/00_Parametros_Mestres.md`.
"""

from __future__ import annotations

import copy
import os
from typing import Any, Dict

import numpy as np
import yaml

# --------------------------------------------------------------------------
# Localização do arquivo mestre
# --------------------------------------------------------------------------
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_MESTRE = os.path.join(_RAIZ, "00_Especificacao_Mestre", "parametros_mestres.yaml")


class Params(dict):
    """Dicionário com acesso por atributo, recursivo e imutável por convenção."""

    def __getattr__(self, item: str) -> Any:
        try:
            valor = self[item]
        except KeyError as exc:  # pragma: no cover - erro de programação
            raise AttributeError(
                f"Parâmetro '{item}' inexistente. Chaves disponíveis: {sorted(self)}"
            ) from exc
        return Params(valor) if isinstance(valor, dict) else valor

    def __dir__(self):  # pragma: no cover - conveniência de REPL
        return list(self) + list(super().__dir__())


def _merge(base: Dict, overlay: Dict) -> Dict:
    """Mescla recursivamente `overlay` sobre `base` (usado pelas variantes)."""
    saida = copy.deepcopy(base)
    for chave, valor in overlay.items():
        if isinstance(valor, dict) and isinstance(saida.get(chave), dict):
            saida[chave] = _merge(saida[chave], valor)
        else:
            saida[chave] = copy.deepcopy(valor)
    return saida


def _derivar(p: Dict) -> Dict:
    """Calcula todos os parâmetros derivados e os grava em `p['derivados']`."""
    esc = p["ambiente"]["escada"]
    E, Pt = esc["espelho_E"], esc["piso_P"]
    esc["blondel_2E_mais_P"] = 2.0 * E + Pt
    esc["passo_D"] = float(np.hypot(E, Pt))
    esc["inclinacao_rad"] = float(np.arctan2(E, Pt))
    esc["inclinacao_deg"] = float(np.degrees(esc["inclinacao_rad"]))

    m = p["massas"]
    m["massa_seca"] = float(
        m["chassi_pvc"] + m["rodas_conjunto"] + m["tracao_conjunto"]
        + m["estercamento_conjunto"] + m["eletronica_potencia"]
        + m["bateria"] + m["caixa_organizadora"]
    )
    m["massa_total"] = m["massa_seca"] + m["carga_util_nominal"]
    m["massa_total_maxima"] = m["massa_seca"] + m["carga_util_maxima"]

    v = p["veiculo"]
    g = 9.80665
    v["peso_total_N"] = m["massa_total"] * g
    v["altura_cg_total"] = (
        (m["massa_seca"] * v["altura_cg_chassi"]
         + m["carga_util_nominal"] * v["altura_cg_carga"]) / m["massa_total"]
    )
    v["lf"] = v["entre_eixos_L"] / 2.0
    v["lr"] = v["entre_eixos_L"] / 2.0
    # Ângulo de tombamento estático longitudinal e lateral (Siegwart, cap. 3)
    v["angulo_tombamento_long_deg"] = float(
        np.degrees(np.arctan2(v["lr"], v["altura_cg_total"]))
    )
    v["angulo_tombamento_lat_deg"] = float(
        np.degrees(np.arctan2(v["bitola_W"] / 2.0, v["altura_cg_total"]))
    )
    # Braço pendular: distância vertical do ponto de fixação ao CG. Positivo =
    # a caixa se auto-nivela; negativo = pêndulo invertido (instável).
    v["braco_pendular"] = v["altura_fixacao_pendular"] - v["altura_cg_total"]
    v["pendulo_estavel"] = bool(v["braco_pendular"] > 0.0)

    r = p["roda"]
    N, rmax = r["num_raios_N"], r["raio_max"]
    r["passo_angular_rad"] = 2.0 * np.pi / N
    # Alcance nariz-a-nariz: maior distância entre dois pontos de contato de
    # raios consecutivos, ambos tocando pela ponta (corda do polígono inscrito).
    r["alcance_nariz_a_nariz"] = 2.0 * rmax * float(np.sin(np.pi / N))
    r["raio_sincrono_exigido"] = esc["passo_D"] / (2.0 * float(np.sin(np.pi / N)))
    r["marcha_sincrona"] = bool(r["alcance_nariz_a_nariz"] >= esc["passo_D"] - 1e-9)
    r["folga_sincronismo"] = r["alcance_nariz_a_nariz"] - esc["passo_D"]
    r["raio_medio_rolamento"] = 0.5 * (rmax + r["raio_cubo"])

    c = p["csts"]
    E_mod = c["modulo_young_pla"] if c["material"].upper() == "PLA" else c["modulo_young_petg"]
    c["modulo_young"] = E_mod
    c["kt_teorico"] = (E_mod * c["largura_b"] * c["espessura_t"] ** 3) / (
        12.0 * c["comprimento_desenrolado_L"]
    )
    c["deflexao_maxima_rad"] = float(np.radians(c["deflexao_maxima_deg"]))

    s = p["suspensao_elastica"]
    s["rigidez_por_roda"] = s["elasticos_por_perna"] * s["rigidez_por_elastico"]

    pw = p["powertrain"]
    mot, i, eta = pw["motor"], pw["reducao"], pw["eficiencia_reducao"]
    # Constante de torque a partir de Kv (SI): Kt = 60 / (2*pi*Kv_rpm_por_volt)
    mot["kt_nm_por_a"] = 60.0 / (2.0 * np.pi * mot["kv_rpm_por_volt"])
    mot["corrente_stall"] = mot["tensao_nominal"] / mot["resistencia_armadura"]
    mot["torque_stall_calc"] = mot["kt_nm_por_a"] * (
        mot["corrente_stall"] - mot["corrente_vazio"]
    )
    pw["torque_stall_saida"] = mot["torque_stall_calc"] * i * eta
    pw["rpm_vazio_saida"] = mot["kv_rpm_por_volt"] * mot["tensao_nominal"] / i
    pw["omega_vazio_saida"] = pw["rpm_vazio_saida"] * 2.0 * np.pi / 60.0

    en = p["energia"]
    en["tensao_nominal_pack"] = en["celulas_serie"] * en["tensao_nominal_celula"]
    en["tensao_cheia_pack"] = en["celulas_serie"] * en["tensao_cheia_celula"]
    en["tensao_corte_pack"] = en["celulas_serie"] * en["tensao_corte_celula"]
    en["capacidade_ah"] = en["celulas_paralelo"] * en["capacidade_celula_ah"]
    en["energia_wh"] = en["capacidade_ah"] * en["tensao_nominal_pack"]
    en["energia_util_wh"] = en["energia_wh"] * (1.0 - en["reserva_operacional"])
    en["resistencia_interna_pack"] = (
        en["resistencia_interna_celula"] * en["celulas_serie"] / en["celulas_paralelo"]
    )

    cin = p["cinematica"]
    cin["grau_manobrabilidade_calc"] = cin["grau_mobilidade_dm"] + cin["grau_dirigibilidade_ds"]

    p["derivados"] = {
        "gravidade": g,
        "raiz_repositorio": _RAIZ,
    }
    return p


def carregar(variante: str | None = None, caminho: str = YAML_MESTRE) -> Params:
    """Carrega os parâmetros mestres aplicando a variante solicitada."""
    with open(caminho, "r", encoding="utf-8") as fh:
        bruto = yaml.safe_load(fh)

    variantes = bruto.pop("variantes", {}) or {}
    alvo = variante or bruto["meta"]["variante_ativa"]
    if alvo not in variantes:
        raise KeyError(
            f"Variante '{alvo}' não declarada. Disponíveis: {sorted(variantes)}"
        )
    overlay = {k: v for k, v in (variantes[alvo] or {}).items() if k != "descricao"}
    resolvido = _merge(bruto, overlay)
    resolvido["meta"] = dict(resolvido["meta"])
    resolvido["meta"]["variante_ativa"] = alvo
    resolvido["meta"]["variantes_disponiveis"] = sorted(variantes)
    resolvido["meta"]["descricao_variante"] = (variantes[alvo] or {}).get("descricao", "")
    return Params(_derivar(resolvido))


#: Parâmetros da variante ativa, prontos para uso.
P = carregar()

# ==========================================================================
# Constantes planas legadas (compatibilidade com o código anterior do simulador)
# ==========================================================================
GRAVITY = P.derivados.gravidade

MASS_TOTAL = P.massas.massa_total
MASS_PAYLOAD = P.massas.carga_util_nominal
MASS_CHASSIS = P.massas.massa_seca
WEIGHT_TOTAL = P.veiculo.peso_total_N

WHEELBASE = P.veiculo.entre_eixos_L
TRACK_WIDTH = P.veiculo.bitola_W
LF = P.veiculo.lf
LR = P.veiculo.lr

# Convenção do referencial do robô: +X direita, +Y cima, +Z ré (frente = -Z)
WHEEL_POSITIONS = {
    "FL": np.array([-TRACK_WIDTH / 2.0, 0.0, -WHEELBASE / 2.0]),
    "FR": np.array([+TRACK_WIDTH / 2.0, 0.0, -WHEELBASE / 2.0]),
    "RL": np.array([-TRACK_WIDTH / 2.0, 0.0, +WHEELBASE / 2.0]),
    "RR": np.array([+TRACK_WIDTH / 2.0, 0.0, +WHEELBASE / 2.0]),
}
WHEEL_IDS = ("FL", "FR", "RL", "RR")

H_CG_CHASSIS = P.veiculo.altura_cg_chassi
H_CG_PAYLOAD = P.veiculo.altura_cg_carga
H_CG_TOTAL = P.veiculo.altura_cg_total
PENDULUM_ARM = P.veiculo.braco_pendular
PENDULUM_DAMPING = P.veiculo.amortecimento_pendular
GROUND_CLEARANCE = P.veiculo.vao_livre_ventre

STAIR_RISER = P.ambiente.escada.espelho_E
STAIR_TREAD = P.ambiente.escada.piso_P
BLONDEL_VALUE = P.ambiente.escada.blondel_2E_mais_P
STAIR_DIAGONAL = P.ambiente.escada.passo_D
STAIR_SLOPE_RAD = P.ambiente.escada.inclinacao_rad

NUM_SPOKES = P.roda.num_raios_N
SPOKE_ANGLE_STEP = P.roda.passo_angular_rad
R_WHEEL_MAX = P.roda.raio_max
R_WHEEL_MIN = P.roda.raio_cubo
R_SPOKE_ARC = P.roda.raio_curvatura_arco

E_MODULUS_PLA = P.csts.modulo_young_pla
CSTS_WIDTH_B = P.csts.largura_b
CSTS_THICKNESS_T = P.csts.espessura_t
CSTS_LENGTH_L = P.csts.comprimento_desenrolado_L
KT_THEORETICAL = P.csts.kt_teorico
KT_PROJETO = P.csts.kt_projeto
KT_EMPIRICAL = P.csts.kt_empirico   # referência do artigo (outra escala)
CT_TORSIONAL = P.csts.amortecimento_ct
CSTS_MAX_DEFLECTION = P.csts.deflexao_maxima_rad
WHEEL_INERTIA = P.csts.inercia_roda

K_RUBBER_BAND = P.suspensao_elastica.rigidez_por_roda
C_RUBBER_BAND = P.suspensao_elastica.amortecimento_por_roda
MAX_SUSP_TRAVEL = P.suspensao_elastica.curso_maximo

MAX_LINEAR_SPEED = P.cinematica.velocidade_maxima
STAIR_SPEED = P.cinematica.velocidade_escada
MAX_STEER_ANGLE = float(np.radians(P.estercamento.angulo_maximo_deg))
STEER_SLEW_RATE = float(np.radians(P.estercamento.taxa_maxima_deg_s))
MOTOR_TORQUE_MAX = P.powertrain.torque_stall_saida
MOTOR_RATED_RPM = P.powertrain.rpm_vazio_saida
COEFF_FRICTION_RUBBER = P.ambiente.piso.mu_borracha_concreto


def resumo() -> str:
    """Resumo textual dos principais parâmetros derivados (uso em CLI/relatórios)."""
    esc, r = P.ambiente.escada, P.roda
    linhas = [
        f"Variante ativa .............. {P.meta.variante_ativa}",
        f"Massa total (nominal) ....... {MASS_TOTAL:.2f} kg  ({WEIGHT_TOTAL:.1f} N)",
        f"Entre-eixos x bitola ........ {WHEELBASE*1000:.0f} x {TRACK_WIDTH*1000:.0f} mm",
        f"Altura do CG ................ {H_CG_TOTAL*1000:.0f} mm",
        f"Tombamento long. / lat. ..... {P.veiculo.angulo_tombamento_long_deg:.1f}° / "
        f"{P.veiculo.angulo_tombamento_lat_deg:.1f}°",
        f"Escada de referência ........ E={esc.espelho_E*1000:.0f} mm, P={esc.piso_P*1000:.0f} mm, "
        f"2E+P={esc.blondel_2E_mais_P*100:.1f} cm, passo D={esc.passo_D*1000:.1f} mm, "
        f"{esc.inclinacao_deg:.1f}°",
        f"Roda ........................ N={r.num_raios_N} raios, "
        f"r_max={r.raio_max*1000:.0f} mm (Φ{2*r.raio_max*1000:.0f} mm), r_cubo={r.raio_cubo*1000:.0f} mm",
        f"Alcance nariz-a-nariz ....... {r.alcance_nariz_a_nariz*1000:.1f} mm "
        f"(exigido {esc.passo_D*1000:.1f} mm) -> "
        f"{'SÍNCRONA' if r.marcha_sincrona else 'ASSÍNCRONA'}",
        f"C-STS ....................... kt_projeto={P.csts.kt_projeto:.2f} N·m/rad "
        f"(artigo: {P.csts.kt_empirico:.2f} N·m/rad em outra escala)",
        f"Torque de stall por roda .... {MOTOR_TORQUE_MAX:.2f} N·m (redução 1:{P.powertrain.reducao:.0f})",
        f"Pack de bateria ............. {P.energia.celulas_serie}S{P.energia.celulas_paralelo}P "
        f"{P.energia.quimica}, {P.energia.capacidade_ah:.1f} Ah, {P.energia.energia_wh:.0f} Wh "
        f"({P.energia.energia_util_wh:.0f} Wh úteis)",
        f"Cinemática (Siegwart) ....... δm={P.cinematica.grau_mobilidade_dm}, "
        f"δs={P.cinematica.grau_dirigibilidade_ds}, δM={P.cinematica.grau_manobrabilidade_dM} "
        f"(holonômico: {'sim' if P.cinematica.holonomico else 'não'})",
    ]
    return "\n".join(linhas)


if __name__ == "__main__":  # pragma: no cover
    print(resumo())
