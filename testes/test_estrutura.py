"""Geometria estrutural derivada e envelope do veículo."""

import numpy as np
import pytest

from simulador_python.config import P
from simulador_python.estrutura import IDS, envelope, geometria_bracos, lista_de_corte


@pytest.fixture(scope="module")
def bracos():
    return geometria_bracos()


def test_existem_quatro_bracos_simetricos(bracos):
    assert set(bracos) == set(IDS)
    fl, fr = bracos["FL"], bracos["FR"]
    assert fl.eixo[0] == pytest.approx(-fr.eixo[0])
    assert fl.eixo[1] == pytest.approx(fr.eixo[1])
    assert fl.eixo[2] == pytest.approx(fr.eixo[2])


def test_eixo_das_rodas_esta_na_altura_do_raio(bracos):
    for b in bracos.values():
        assert b.eixo[1] == pytest.approx(P.roda.raio_max)


def test_abracadeira_no_terco_superior_da_caixa(bracos):
    for b in bracos.values():
        assert b.abracadeira[1] == pytest.approx(P.veiculo.altura_fixacao_pendular)


def test_vertice_e_o_ponto_mais_alto_do_braco(bracos):
    """A triangulação em V invertido exige o ápice acima das duas extremidades."""
    for b in bracos.values():
        assert b.vertice[1] > b.abracadeira[1]
        assert b.vertice[1] > b.manga[1]


def test_hastes_tem_comprimento_construivel(bracos):
    for b in bracos.values():
        assert 0.08 < b.haste_superior < 0.60
        assert 0.08 < b.haste_inferior < 0.60


def test_lista_de_corte_inclui_folga_de_encaixe(bracos):
    itens = {i["peca"]: i for i in lista_de_corte()}
    sup = itens["Haste superior (ascendente)"]
    assert sup["comprimento_mm"] > bracos["FL"].haste_superior * 1000
    assert sum(i["qtd"] for i in lista_de_corte()) == 8


def test_veiculo_passa_na_porta_estreita():
    e = envelope()
    assert e["passa_em_porta"], f"largura {e['largura_m']:.3f} m não passa em 0,80 m"
    assert e["folga_na_porta_mm"] > 50, "folga insuficiente para pilotagem remota"


def test_veiculo_passa_no_corredor():
    assert envelope()["passa_em_corredor"]


def test_envelope_coerente_com_os_parametros():
    e = envelope()
    assert e["comprimento_m"] == pytest.approx(
        P.veiculo.entre_eixos_L + 2 * P.roda.raio_max)
    assert e["altura_m"] > P.veiculo.vao_livre_ventre
