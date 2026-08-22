"""Distribuição de cargas, estabilidade e comparação com skid-steer."""

import numpy as np
import pytest

from simulador_python.config import P
from simulador_python.terramechanics import TerramecanicaWong, carga_projeto_por_roda


@pytest.fixture
def terra():
    return TerramecanicaWong()


def test_cargas_somam_a_componente_normal_do_peso(terra):
    for pitch in (0.0, 0.2, 0.5):
        fz = terra.cargas_normais(pitch=pitch)
        assert sum(fz.values()) == pytest.approx(terra.peso * np.cos(pitch), rel=1e-9)


def test_plano_distribui_igualmente(terra):
    fz = terra.cargas_normais()
    assert np.allclose(list(fz.values()), terra.peso / 4.0)


def test_subida_transfere_carga_para_tras(terra):
    """Na subida quem carrega é o eixo traseiro — é ele que faz o içamento."""
    fz = terra.cargas_normais(pitch=P.ambiente.escada.inclinacao_rad)
    assert fz["RL"] > fz["FL"] and fz["RR"] > fz["FR"]


def test_carga_de_projeto_e_a_da_roda_traseira(terra):
    fz = terra.cargas_normais(pitch=P.ambiente.escada.inclinacao_rad)
    assert carga_projeto_por_roda() == pytest.approx(max(fz["RL"], fz["RR"]))
    assert carga_projeto_por_roda() < terra.peso / 2.0


def test_roll_transfere_carga_para_o_lado_de_baixo(terra):
    fz = terra.cargas_normais(roll=0.2)
    assert fz["FR"] > fz["FL"] and fz["RR"] > fz["RL"]


def test_roda_descola_no_angulo_de_tombamento(terra):
    limite = terra.angulo_tombamento_longitudinal()
    fz = terra.cargas_normais(pitch=limite + 0.05)
    assert fz["FL"] == 0.0 and fz["FR"] == 0.0


def test_reacoes_nunca_sao_negativas(terra):
    for pitch in np.linspace(-1.2, 1.2, 25):
        for roll in np.linspace(-0.8, 0.8, 9):
            assert all(v >= 0.0 for v in terra.cargas_normais(pitch, roll).values())


def test_atrito_disponivel_cobre_a_escada_seca_mas_nao_a_molhada(terra):
    exigido = terra.atrito_minimo_exigido(P.ambiente.escada.inclinacao_rad, 0.15)
    assert exigido < P.ambiente.piso.mu_borracha_concreto
    assert exigido > P.ambiente.piso.mu_borracha_concreto_molhado
    assert exigido > P.ambiente.piso.mu_borracha_marmore_polido


def test_skid_steer_gasta_mais_e_a_diferenca_cresce_em_curva_fechada(terra):
    aberta = terra.comparar_com_skid_steer(0.8, 3.0)
    fechada = terra.comparar_com_skid_steer(0.8, 0.6)
    assert aberta["potencia_skid_w"] > aberta["potencia_4ws_w"]
    assert fechada["economia_percentual"] > aberta["economia_percentual"]


def test_margem_de_tombamento_na_escada_atende_ao_kpi(terra):
    estado = terra.avaliar(pitch=P.ambiente.escada.inclinacao_rad, crr=0.15)
    assert np.degrees(estado.margem_tombamento_long) >= P.kpi.margem_tombamento_deg.minimo
