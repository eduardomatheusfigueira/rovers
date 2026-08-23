"""Marcha da roda de raios curvos: condição síncrona, robustez e conservação."""

import numpy as np
import pytest

from simulador_python.config import P
from simulador_python.geometria_escada import (PerfilEscada, PerfilMeioFio, PerfilPlano,
                                               RodaRaiosCurvos, SimuladorMarcha,
                                               avaliar_projeto, avaliar_robustez)


def test_perfil_da_escada_tem_alturas_corretas():
    e = PerfilEscada(espelho=0.17, piso=0.30, num_degraus=4)
    assert e.altura(-0.5) == pytest.approx(0.0)
    assert e.altura(0.05) == pytest.approx(0.17)
    assert e.altura(0.35) == pytest.approx(0.34)
    assert e.altura(5.0) == pytest.approx(4 * 0.17)
    assert e.passo == pytest.approx(np.hypot(0.17, 0.30))


def test_narizes_estao_espacados_de_um_passo():
    e = PerfilEscada(num_degraus=5)
    n = np.array(e.narizes())
    d = np.hypot(*np.diff(n, axis=0).T)
    assert np.allclose(d, e.passo)


def test_alcance_nariz_a_nariz_bate_com_a_formula():
    for N in (3, 4, 5):
        r = RodaRaiosCurvos(num_raios=N, raio_max=0.2, raio_cubo=0.06)
        assert r.alcance_nariz_a_nariz == pytest.approx(2 * 0.2 * np.sin(np.pi / N))
        assert RodaRaiosCurvos.raio_sincrono(0.3448, N) == pytest.approx(
            0.3448 / (2 * np.sin(np.pi / N)))


def test_roda_legado_phi300_nao_escala_o_degrau_de_referencia():
    """Achado A-01 da auditoria: a roda original é geometricamente insuficiente."""
    rb = avaliar_robustez(3, 0.150, 0.17, 0.30, raio_cubo=0.045, num_fases=8, degraus_alvo=3)
    assert not rb.sincrona
    assert rb.taxa_sucesso == 0.0


def test_roda_adotada_escala_toda_a_familia_de_blondel():
    for E, Pt in [(0.16, 0.32), (0.17, 0.30), (0.18, 0.28)]:
        rb = avaliar_robustez(3, P.roda.raio_max, E, Pt, raio_cubo=P.roda.raio_cubo,
                              num_fases=8, degraus_alvo=3)
        assert rb.sincrona, f"não síncrona em {E}x{Pt}"
        assert rb.taxa_sucesso == 1.0, f"{rb.taxa_sucesso:.0%} em {E}x{Pt}"


def test_marcha_avanca_monotonicamente():
    res = avaliar_projeto(3, P.roda.raio_max, 0.17, 0.30,
                          raio_cubo=P.roda.raio_cubo, degraus_alvo=3)
    x = res.trajetoria_cubo[:, 0]
    assert np.all(np.diff(x) >= -1e-9), "o cubo não pode recuar durante a marcha"
    assert res.sucesso


def test_cubo_nunca_penetra_o_terreno():
    roda = RodaRaiosCurvos()
    escada = PerfilEscada(num_degraus=6)
    sim = SimuladorMarcha(roda, escada)
    res = sim.simular(x_inicial=-0.8, degraus_alvo=3)
    for cubo, psi in zip(res.trajetoria_cubo, res.psi):
        pen = escada.penetracao(roda.pontos(cubo, psi))
        assert pen.max() < 1e-4, "interferência da roda com o terreno"


def test_ripple_em_piso_plano_e_o_da_roda_sem_aro():
    """Sem aro, o cubo cai r_max*(1-cos(pi/N)) — o que inviabiliza carga sensível."""
    roda = RodaRaiosCurvos()
    res = SimuladorMarcha(roda, PerfilPlano()).simular(x_inicial=0.0, max_voltas=2.0)
    teorico = roda.raio_max * (1 - np.cos(np.pi / roda.num_raios))
    assert res.ripple_cubo == pytest.approx(teorico, rel=0.25)
    assert res.ripple_cubo > 0.08, "ripple grande é justamente o motivo do aro elástico"


def test_meio_fio_e_transposto():
    roda = RodaRaiosCurvos()
    terreno = PerfilMeioFio(altura_degrau=P.ambiente.meio_fio.altura_maxima)
    res = SimuladorMarcha(roda, terreno).simular(x_inicial=-0.5, max_voltas=4.0)
    assert res.trajetoria_cubo[-1, 1] > terreno.altura_degrau
