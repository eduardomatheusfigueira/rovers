"""Cadeia de tração, bateria e orçamento de energia."""

import numpy as np
import pytest

from simulador_python.config import P
from simulador_python.powertrain import (ModeloTermicoMotor, MotorCC, OrcamentoEnergia,
                                         PackBateria, TrechoMissao, missao_parquetec)


def test_curva_do_motor_e_monotona_decrescente():
    c = MotorCC().curva()
    assert np.all(np.diff(c["torque"]) <= 1e-9)
    assert c["torque"][0] > c["torque"][-1]


def test_torque_de_stall_bate_com_a_definicao():
    m = MotorCC()
    assert m.ponto_operacao(1e-6)["torque_saida"] == pytest.approx(m.torque_stall_saida, rel=0.02)


def test_corrente_para_torque_e_inversa_do_ponto_de_operacao():
    m = MotorCC()
    op = m.ponto_operacao(2.0)
    assert m.corrente_para_torque(op["torque_saida"]) == pytest.approx(op["corrente"], rel=1e-6)


def test_rendimento_entre_zero_e_um():
    c = MotorCC().curva()
    assert np.all((c["rendimento"] >= 0) & (c["rendimento"] <= 1))


def test_margem_de_torque_na_escada_atende_ao_kpi():
    orc = OrcamentoEnergia()
    r = orc.avaliar_missao(missao_parquetec())
    assert r["margem_torque_minima"] >= P.kpi.margem_torque.minimo
    assert r["viavel"]


def test_autonomia_atende_ao_kpi():
    a = OrcamentoEnergia().autonomia_ciclo_misto()
    assert a["autonomia_min"] >= P.kpi.autonomia_min.minimo


def test_missao_cabe_na_energia_util():
    orc = OrcamentoEnergia()
    r = orc.avaliar_missao(missao_parquetec())
    assert r["energia_total_wh"] < orc.pack.energia_util_wh


def test_tensao_do_pack_cai_com_a_corrente():
    p = PackBateria()
    assert p.tensao_sob_carga(30.0) < p.tensao_sob_carga(0.0)
    assert p.tensao_sob_carga(0.0) <= p.serie * p.tensao_cheia_celula + 1e-9


def test_limite_termico_permite_um_lance_mas_nao_operacao_continua():
    t = ModeloTermicoMotor()
    orc = OrcamentoEnergia()
    corrente_escada = max(r.corrente_total for r in
                          orc.avaliar_missao(missao_parquetec())["trechos"]) / 4.0
    limite = t.tempo_limite(corrente_escada)
    assert limite > 11.0, "não sustenta nem um lance de 8 degraus"
    assert limite < 300.0, "sem restrição térmica o modelo perdeu a física do problema"
    assert t.corrente_continua_admissivel() < corrente_escada


def test_rampa_exige_mais_torque_que_plano():
    orc = OrcamentoEnergia()
    plano = orc.avaliar_trecho(TrechoMissao("plano", 10, 0.0, 0.8))
    rampa = orc.avaliar_trecho(TrechoMissao("rampa", 10, 15.0, 0.8))
    assert rampa.torque_por_roda > plano.torque_por_roda
