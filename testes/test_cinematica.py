"""Cinemática 4WS: ICR, ausência de arrasto e classificação de Siegwart."""

import numpy as np
import pytest

from simulador_python.kinematics import (IDS, Cinematica4WS, classificar_siegwart,
                                         custo_reconfiguracao, posicoes_rodas)


@pytest.fixture
def cin():
    return Cinematica4WS()


@pytest.mark.parametrize("vx,vy,omega", [(0.8, 0.0, 0.5), (0.5, 0.3, -0.4),
                                         (1.0, 0.0, 0.0), (0.0, 0.0, 0.8)])
def test_sem_arrasto_lateral(cin, vx, vy, omega):
    """A solução de cinemática inversa anula a velocidade perpendicular à roda."""
    cmd = cin.inversa(vx, vy, omega, modo="ackermann")
    assert np.max(np.abs(cin.residuo_deslizamento(cmd, vx, vy, omega))) < 1e-12


@pytest.mark.parametrize("vx,vy,omega", [(0.8, 0.0, 0.5), (0.5, 0.1, 0.3)])
def test_odometria_recupera_o_comando(cin, vx, vy, omega):
    """Cinemática direta é a inversa da inversa (ida e volta), sem saturação."""
    cmd = cin.inversa(vx, vy, omega, modo="ackermann")
    assert not cmd.saturado
    estimado = cin.direta(cmd.angulos, cmd.velocidades)
    assert np.allclose(estimado, [vx, vy, omega], atol=1e-9)


def test_saturacao_de_estercamento_degrada_a_odometria(cin):
    """Quando um servo satura, a odometria passa a errar: o firmware precisa sinalizar."""
    cmd = cin.inversa(0.6, -0.2, 0.9, modo="ackermann")
    assert cmd.saturado
    erro = np.abs(cin.direta(cmd.angulos, cmd.velocidades) - np.array([0.6, -0.2, 0.9]))
    assert erro.max() > 1e-9


def test_icr_e_o_ponto_de_velocidade_nula(cin):
    vx, vy, omega = 0.7, 0.1, 0.6
    icr = np.array(cin.icr(vx, vy, omega))
    v_no_icr = np.array([vx - omega * icr[1], vy + omega * icr[0]])
    assert np.allclose(v_no_icr, 0.0, atol=1e-12)


def test_translacao_pura_tem_icr_no_infinito(cin):
    assert cin.icr(1.0, 0.0, 0.0) is None


def test_modo_caranguejo_alinha_as_quatro_rodas(cin):
    cmd = cin.inversa(0.6, 0.6, 0.0, modo="crab")
    angulos = [cmd.angulos[i] for i in IDS]
    assert np.allclose(angulos, angulos[0])


def test_modo_escada_zera_o_estercamento(cin):
    cmd = cin.inversa(0.25, 0.0, 0.0, modo="stair")
    assert all(abs(cmd.angulos[i]) < 1e-12 for i in IDS)
    assert all(abs(cmd.velocidades[i] - 0.25) < 1e-12 for i in IDS)


def test_giro_no_eixo_cabe_no_curso_dos_servos(cin):
    """O ângulo tangencial exigido é atan2(L/2, W/2) — precisa caber no limite."""
    cmd = cin.inversa(0.0, 0.0, 1.0, modo="spin")
    assert not cmd.saturado, "o curso de esterçamento não permite giro no próprio eixo"


def test_classificacao_de_siegwart_coordenada():
    r = classificar_siegwart(coordenado=True)
    assert (r["delta_m"], r["delta_s"], r["delta_M"]) == (1, 2, 3)
    assert r["holonomico"] is False
    assert "Two-Steer" in r["categoria"]


def test_descoordenacao_trava_o_veiculo():
    r = classificar_siegwart(coordenado=False)
    assert r["posto_C1s"] == 3 and r["delta_m"] == 0


def test_erro_de_servo_gera_arrasto_proporcional(cin):
    a = cin.escorregamento_por_descoordenacao(1.0, 0.0, 0.4, 1.0)
    b = cin.escorregamento_por_descoordenacao(1.0, 0.0, 0.4, 2.0)
    assert b == pytest.approx(2 * a, rel=0.05)
    assert a > 0.0


def test_troca_de_modo_custa_tempo():
    """δs=2 implica parar e reorientar: o custo não pode ser zero."""
    assert custo_reconfiguracao("ackermann", "crab") > 0.2
    assert custo_reconfiguracao("crab", "crab") == 0.0
