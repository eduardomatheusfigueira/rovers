"""C-STS, aro elástico e dinâmica da carga."""

import numpy as np
import pytest

from simulador_python.config import P
from simulador_python.csts import (MATERIAIS, DinamicaCSTS, dimensionar_csts,
                                   modelo_impacto)
from simulador_python.geometria_escada import PerfilEscada, PerfilPlano
from simulador_python.multibody_dynamics import (ConfiguracaoSuspensao, SimuladorSagital,
                                                 gerar_excitacao, metricas)


@pytest.fixture(scope="module")
def espiral():
    return dimensionar_csts(P.csts.torque_projeto, P.csts.deflexao_projeto_deg,
                            P.csts.material, raio_externo=P.csts.raio_externo_espiral)


def test_rigidez_de_projeto_bate_com_torque_sobre_deflexao(espiral):
    assert espiral.kt_efetivo == pytest.approx(
        P.csts.torque_projeto / np.radians(P.csts.deflexao_projeto_deg), rel=1e-9)


def test_espiral_cabe_no_cubo_e_tem_fator_de_seguranca(espiral):
    assert espiral.cabe_no_cubo
    assert espiral.fator_seguranca >= 2.0
    assert espiral.raio_externo < P.roda.raio_cubo


def test_rigidez_do_artigo_seria_absurda_nesta_escala():
    """Achado A-04: kt do artigo (0,55 N·m/rad) satura o batente por 10x."""
    deflexao = P.csts.torque_projeto / P.csts.kt_empirico
    assert np.degrees(deflexao) > 10 * P.csts.deflexao_maxima_deg


def test_kt_escala_com_o_cubo_da_espessura():
    a = dimensionar_csts(5.0, 30.0, "PETG")
    b = dimensionar_csts(10.0, 30.0, "PETG")
    razao_kt = b.kt_efetivo / a.kt_efetivo
    razao_geom = (b.espessura_t ** 3 / b.comprimento_L) / (a.espessura_t ** 3 / a.comprimento_L)
    assert razao_geom == pytest.approx(razao_kt, rel=1e-6)


@pytest.mark.parametrize("material", sorted(MATERIAIS))
def test_dimensionamento_funciona_para_todos_os_materiais(material):
    e = dimensionar_csts(5.0, 30.0, material)
    assert e.espessura_t > 0 and e.comprimento_L > 0


def test_energia_armazenada_e_quadratica(espiral):
    u1 = espiral.energia_armazenada(0.1)
    u2 = espiral.energia_armazenada(0.2)
    assert u2 == pytest.approx(4 * u1, rel=1e-9)


def test_impacto_e_reduzido_pelos_dois_estagios(espiral):
    r = modelo_impacto(0.089, espiral)
    assert r.aceleracao_completa < r.aceleracao_csts < r.aceleracao_rigida
    assert r.reducao_percentual > 80.0


def test_batente_limita_a_deflexao(espiral):
    d = DinamicaCSTS(espiral, ativo=True)
    for _ in range(4000):
        d.passo(omega_motor=6.0, torque_resistente=40.0, dt=1e-4)
    assert abs(d.deflexao) < 3 * P.csts.deflexao_maxima_rad


def test_cubo_rigido_transmite_tudo(espiral):
    d = DinamicaCSTS(espiral, ativo=False)
    t = d.passo(omega_motor=5.0, torque_resistente=3.3, dt=1e-3)
    assert t == pytest.approx(3.3)
    assert d.energia == 0.0


# --- dinâmica completa ---------------------------------------------------
@pytest.mark.parametrize("com_aro,limite", [(True, 1.0), (False, 3.0)])
def test_aro_elastico_e_indispensavel_em_piso_plano(com_aro, limite):
    exc = gerar_excitacao(terreno=PerfilPlano(), com_aro=com_aro,
                          x_inicial=0.0, degraus_alvo=None)
    cfg = ConfiguracaoSuspensao(com_csts=True, com_elasticos=True, com_aro=com_aro)
    m = metricas(SimuladorSagital(cfg).simular(exc, 0.9, 1.6))
    if com_aro:
        assert m["pico_vertical_g"] < limite
    else:
        assert m["pico_vertical_g"] > limite


def test_carga_respeita_o_limite_de_choque_na_escada():
    exc = gerar_excitacao(terreno=PerfilEscada(num_degraus=6), com_aro=True,
                          x_inicial=-0.8, degraus_alvo=4)
    cfg = ConfiguracaoSuspensao(com_csts=True, com_elasticos=True, com_aro=True)
    m = metricas(SimuladorSagital(cfg).simular(exc, P.cinematica.velocidade_escada, 2.2))
    assert m["pico_vertical_g"] < P.controle.limite_choque_carga_g


def test_passo_de_integracao_respeita_a_frequencia_natural():
    for cfg in (ConfiguracaoSuspensao(True, True, True),
                ConfiguracaoSuspensao(False, False, False)):
        sim = SimuladorSagital(cfg)
        k = max(cfg.k_aro(), cfg.k_elasticos())
        m = min(sim.m_nao_suspensa, sim.m_suspensa + sim.m_carga)
        assert sim.passo_estavel() * np.sqrt(2 * k / m) <= 0.1 + 1e-12
