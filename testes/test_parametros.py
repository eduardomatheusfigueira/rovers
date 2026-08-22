"""Consistência do arquivo mestre de parâmetros e dos valores derivados."""

import numpy as np
import pytest

from simulador_python import config as cfg
from simulador_python.config import P


def test_todas_as_variantes_carregam():
    for variante in P.meta.variantes_disponiveis:
        p = cfg.carregar(variante)
        assert p.massas.massa_total > 0
        assert p.roda.raio_max > p.roda.raio_cubo


def test_massa_total_e_soma_das_partes():
    m = P.massas
    soma = (m.chassi_pvc + m.rodas_conjunto + m.tracao_conjunto + m.estercamento_conjunto
            + m.eletronica_potencia + m.bateria + m.caixa_organizadora)
    assert m.massa_seca == pytest.approx(soma, rel=1e-9)
    assert m.massa_total == pytest.approx(soma + m.carga_util_nominal, rel=1e-9)


def test_escada_de_referencia_respeita_blondel():
    esc = P.ambiente.escada
    assert 0.63 <= esc.blondel_2E_mais_P <= 0.65
    assert 0.16 <= esc.espelho_E <= 0.18
    assert 0.28 <= esc.piso_P <= 0.32
    assert esc.passo_D == pytest.approx(np.hypot(esc.espelho_E, esc.piso_P))


def test_manobrabilidade_soma_corretamente():
    """δM = δm + δs. O documento original declarava δm=2, δs=4, δM=3 (2+4≠3)."""
    c = P.cinematica
    assert c.grau_manobrabilidade_dM == c.grau_mobilidade_dm + c.grau_dirigibilidade_ds
    assert c.grau_dirigibilidade_ds <= 2, "Siegwart: δs <= 2 com rodas padrão direcionais"
    assert c.holonomico is False, "δM=3 com δs=2 não é holonomia instantânea"


def test_entre_eixos_e_multiplo_do_passo_do_degrau():
    """Trava de fase entre eixo dianteiro e traseiro na escada."""
    k = P.veiculo.fator_fase_escada_k
    assert P.veiculo.entre_eixos_L == pytest.approx(k * P.ambiente.escada.passo_D, abs=0.005)


def test_vao_livre_supera_o_espelho():
    assert P.veiculo.vao_livre_ventre > P.ambiente.escada.espelho_E


def test_pendulo_e_estavel():
    """A caixa só se auto-nivela se o CG ficar ABAIXO do ponto de fixação."""
    assert P.veiculo.braco_pendular > 0.0
    assert P.veiculo.pendulo_estavel
    assert P.veiculo.altura_cg_total < P.veiculo.altura_fixacao_pendular


def test_carga_esta_dentro_da_caixa():
    """O CG da carga precisa estar acima do fundo da caixa — não flutuando."""
    fundo = P.veiculo.vao_livre_ventre
    assert fundo < P.veiculo.altura_cg_carga < fundo + P.veiculo.altura_caixa


def test_margem_de_tombamento_atende_ao_kpi():
    inclinacao = P.ambiente.escada.inclinacao_deg
    margem = P.veiculo.angulo_tombamento_long_deg - inclinacao
    assert margem >= P.kpi.margem_tombamento_deg.minimo


def test_curso_da_suspensao_cobre_a_queda_da_marcha():
    """O curso precisa absorver a energia da queda de cubo da marcha."""
    from simulador_python.geometria_escada import (PerfilEscada, RodaRaiosCurvos,
                                                   SimuladorMarcha)
    res = SimuladorMarcha(RodaRaiosCurvos(), PerfilEscada(num_degraus=6)).simular(
        x_inicial=-0.8, degraus_alvo=3)
    energia = P.massas.massa_total * 9.80665 * res.queda_maxima
    k_total = P.suspensao_elastica.rigidez_por_roda * 4.0
    curso_necessario = np.sqrt(2.0 * energia / k_total)
    assert P.suspensao_elastica.curso_maximo >= 0.9 * curso_necessario
