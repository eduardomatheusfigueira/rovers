"""
Verificação dos nós de controle ROS 2 — sem precisar de ROS instalado.

A lógica de cinemática, molas passivas e supervisão foi deliberadamente separada
dos nós `rclpy` justamente para poder ser testada aqui. O que roda no Gazebo é o
mesmo código verificado abaixo.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

from simulador_python.config import P
from simulador_python.kinematics import Cinematica4WS

sys.path.insert(0, os.path.join(P.derivados.raiz_repositorio,
                                "ros2_ws", "src", "rover_frugal_control"))

from rover_frugal_control.cinematica_4ws import (  # noqa: E402
    IDS, Geometria, resolver, residuo_deslizamento, tempo_reconfiguracao)
from rover_frugal_control.molas_passivas import MolaLinear, MolaTorsional  # noqa: E402
from rover_frugal_control.supervisor import (  # noqa: E402
    Entradas, Estado, Limites, ModeloTermico, Supervisor)


@pytest.fixture(scope="module")
def geo():
    return Geometria(P.veiculo.entre_eixos_L, P.veiculo.bitola_W, P.roda.raio_max,
                     math.radians(P.estercamento.angulo_maximo_deg))


# =========================================================================
# Cinemática — verificação cruzada ENS-01
# =========================================================================
@pytest.mark.parametrize("modo", ["ackermann", "crab", "spin", "stair"])
@pytest.mark.parametrize("v", [(0.8, 0.0, 0.5), (0.5, 0.3, -0.4),
                               (1.0, 0.0, 0.0), (0.0, 0.0, 0.9), (0.25, 0.0, 0.0)])
def test_no_ros_bate_com_o_simulador(geo, modo, v):
    """ENS-01 em software: firmware/ROS e simulador precisam concordar.

    Critério de campo do ensaio: 0,1° (1,7e-3 rad) e 1 mm/s.
    """
    vx, vy, om = v
    ros = resolver(geo, vx, vy, om, modo)
    ref = Cinematica4WS().inversa(vx, vy, om, modo)
    for w in IDS:
        assert ros.angulos[w] == pytest.approx(ref.angulos[w], abs=1e-9)
        assert ros.velocidades_rodas[w] * P.roda.raio_max == pytest.approx(
            ref.velocidades[w], abs=1e-9)


@pytest.mark.parametrize("v", [(0.8, 0.0, 0.5), (0.6, -0.2, 0.3)])
def test_solucao_nao_tem_arrasto_lateral(geo, v):
    cmd = resolver(geo, *v, "ackermann")
    assert residuo_deslizamento(geo, cmd, *v) < 1e-12


def test_velocidade_de_roda_e_coerente_com_o_raio(geo):
    """v = ω·r: comandar rad/s errado é o erro clássico de controlador de roda."""
    cmd = resolver(geo, 1.0, 0.0, 0.0, "stair")
    for w in IDS:
        assert cmd.velocidades_rodas[w] == pytest.approx(1.0 / P.roda.raio_max)


def test_giro_no_eixo_nao_satura_o_servo(geo):
    assert not resolver(geo, 0.0, 0.0, 1.0, "spin").saturado


def test_troca_de_modo_custa_tempo(geo):
    """δs = 2: o rover não é holonômico e precisa parar para reorientar."""
    ack = resolver(geo, 0.5, 0.0, 0.0, "ackermann").angulos
    crab = resolver(geo, 0.4, 0.4, 0.0, "crab").angulos
    t = tempo_reconfiguracao(geo, ack, crab, P.estercamento.velocidade_servo)
    assert t > 0.1


# =========================================================================
# Molas passivas
# =========================================================================
def test_suspensao_sustenta_o_peso_no_afundamento_estatico():
    m = MolaLinear(P.suspensao_elastica.rigidez_por_roda,
                   P.suspensao_elastica.amortecimento_por_roda,
                   P.suspensao_elastica.curso_maximo)
    carga = P.veiculo.peso_total_N / 4.0
    x = m.afundamento_estatico(carga)
    assert m.esforco(x, 0.0) == pytest.approx(-carga, rel=1e-9)
    assert 0.15 * m.curso < x < 0.35 * m.curso, "afundamento fora da boa prática (20-30%)"


def test_batente_endurece_fora_do_curso():
    """O que define o batente é a rigidez INCREMENTAL, não a força absoluta."""
    m = MolaLinear(1000.0, 25.0, 0.090)
    d = 0.002
    k_dentro = (m.esforco(0.080, 0.0) - m.esforco(0.080 + d, 0.0)) / d
    k_fora = (m.esforco(0.095, 0.0) - m.esforco(0.095 + d, 0.0)) / d
    assert k_dentro == pytest.approx(m.rigidez, rel=1e-6)
    assert k_fora > 10 * k_dentro


def test_amortecimento_opoe_a_velocidade():
    m = MolaLinear(1000.0, 25.0, 0.090)
    assert m.esforco(0.02, +0.5) < m.esforco(0.02, 0.0) < m.esforco(0.02, -0.5)


def test_csts_usa_a_rigidez_de_projeto():
    c = MolaTorsional(P.csts.kt_projeto, P.csts.amortecimento_ct,
                      P.csts.deflexao_maxima_rad)
    theta = P.csts.torque_projeto / P.csts.kt_projeto
    assert c.esforco(theta, 0.0) == pytest.approx(-P.csts.torque_projeto, rel=1e-9)
    # kt_projeto no arquivo mestre é arredondado; 0,1% de tolerância basta
    assert math.degrees(theta) == pytest.approx(P.csts.deflexao_projeto_deg, rel=1e-3)
    assert theta < P.csts.deflexao_maxima_rad, "deflexão de projeto bate no batente"


def test_energia_do_csts_e_quadratica():
    c = MolaTorsional(P.csts.kt_projeto, 0.08, 0.6)
    assert c.energia(0.4) == pytest.approx(4 * c.energia(0.2))


# =========================================================================
# Supervisor
# =========================================================================
def _armar(sup: Supervisor, e: Entradas) -> None:
    for _ in range(3):
        sup.passo(e, 0.01)


def test_limiar_de_arfagem_depende_do_modo():
    sup = Supervisor()
    assert sup.limiar_arfagem("stair") > sup.limiar_arfagem("ackermann")
    assert sup.limiar_arfagem("stair") >= P.controle.arfagem_esperada_escada_deg


def test_arfagem_normal_de_escada_nao_dispara_protecao():
    """43° é a arfagem NORMAL na subida — um limiar único de 40° abortaria tudo."""
    sup = Supervisor()
    e = Entradas(modo="stair", piso_seco_confirmado=True,
                 arfagem_deg=P.controle.arfagem_esperada_escada_deg)
    _armar(sup, e)
    s = sup.passo(e, 0.01)
    assert s.estado is Estado.OPERACAO_ESCADA
    assert s.tracao_liberada


def test_mesma_arfagem_em_piso_dispara_protecao():
    sup = Supervisor()
    e = Entradas(modo="ackermann", arfagem_deg=P.controle.arfagem_esperada_escada_deg)
    _armar(sup, e)
    s = sup.passo(e, 0.01)
    assert s.estado is Estado.PROTECAO
    assert not s.tracao_liberada and s.freio_dinamico


def test_modo_escada_bloqueado_sem_confirmar_piso_seco():
    """μ exigido é 0,72; concreto molhado dá 0,55 (achado A-10)."""
    sup = Supervisor()
    e = Entradas(modo="stair", piso_seco_confirmado=False)
    _armar(sup, e)
    s = sup.passo(e, 0.01)
    assert s.estado is Estado.ARMADO
    assert any("piso seco" in a for a in s.alertas)


def test_failsafe_por_perda_de_enlace_aciona_freio():
    sup = Supervisor()
    e = Entradas(idade_enlace_s=0.5)
    _armar(sup, e)
    s = sup.passo(e, 0.01)
    assert s.estado is Estado.FAILSAFE
    assert s.freio_dinamico, "rodas livres em rampa fazem o rover descer sozinho"


def test_rearme_e_sempre_explicito():
    sup = Supervisor()
    e = Entradas(idade_enlace_s=0.5)
    _armar(sup, e)
    e.idade_enlace_s = 0.0
    s = sup.passo(e, 0.01)
    assert s.estado is Estado.FAILSAFE, "não pode sair do failsafe sozinho"
    e.rearme_solicitado = True
    s = sup.passo(e, 0.01)
    assert s.estado is Estado.ARMADO


def test_protecao_termica_por_integral():
    """O dano ao esmalte é integral: corrente instantânea não é critério."""
    sup = Supervisor()
    e = Entradas(modo="stair", piso_seco_confirmado=True, corrente_por_motor=9.2)
    _armar(sup, e)
    for _ in range(int(60.0 / 0.01)):     # 60 s de subida contínua
        s = sup.passo(e, 0.01)
        if s.estado is Estado.RESFRIAMENTO:
            break
    assert s.estado is Estado.RESFRIAMENTO
    assert not s.tracao_liberada

    e.corrente_por_motor = 0.0
    for _ in range(int(600.0 / 0.01)):
        s = sup.passo(e, 0.01)
        if s.estado is not Estado.RESFRIAMENTO:
            break
    assert s.estado is Estado.OPERACAO_ESCADA, "deve retomar após resfriar"


def test_corrente_de_cruzeiro_nao_dispara_termica():
    sup = Supervisor()
    e = Entradas(modo="ackermann", corrente_por_motor=2.0)
    _armar(sup, e)
    for _ in range(int(1800.0 / 0.01)):
        s = sup.passo(e, 0.01)
    assert s.estado is Estado.OPERACAO_PLANO
    assert sup.termico.temperatura < sup.termico.limite


def test_modelo_termico_do_supervisor_bate_com_o_do_dimensionamento():
    from simulador_python.powertrain import ModeloTermicoMotor
    ref = ModeloTermicoMotor()
    sup_t = ModeloTermico(resistencia=ref.resistencia, r_termica=ref.r_termica,
                          c_termica=ref.c_termica, ambiente=ref.temp_ambiente)
    corrente, dt = 7.2, 0.01
    for _ in range(int(30.0 / dt)):
        sup_t.passo(corrente, dt)
    assert sup_t.temperatura == pytest.approx(
        ref.temperatura(corrente, 30.0), rel=0.02)
