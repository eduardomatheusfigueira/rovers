"""Testes de integração: a cadeia completa precisa rodar e produzir artefatos."""

import os

import pytest

from simulador_python.config import P


def test_relatorio_e_gerado(tmp_path):
    from simulador_python.relatorio import gerar
    caminho = gerar(str(tmp_path))
    assert os.path.exists(caminho)
    texto = open(caminho, encoding="utf-8").read()
    assert "Relatório de Engenharia" in texto
    assert f"Φ {2*P.roda.raio_sincrono_exigido*1000:.0f} mm" in texto or "síncrona" in texto
    for figura in ("b1_dimensionamento_roda.png", "b4_robustez_fase.png",
                   "b5_tracao.png", "b6_manobra.png"):
        assert os.path.exists(os.path.join(str(tmp_path), figura))


def test_cli_de_parametros_roda():
    from simulador_python import config
    assert "Variante ativa" in config.resumo()


def test_parametros_js_estao_sincronizados():
    """O protótipo 3D precisa consumir os MESMOS números do arquivo mestre."""
    import json
    import re
    caminho = os.path.join(P.derivados.raiz_repositorio, "prototipo_3d", "parametros.js")
    if not os.path.exists(caminho):
        pytest.skip("parametros.js ainda não gerado (rode ferramentas/gerar_parametros_js.py)")
    texto = open(caminho, encoding="utf-8").read()
    bruto = re.search(r"export const PARAMETROS = (\{.*?\});", texto, re.S).group(1)
    dados = json.loads(bruto)
    assert dados["roda"]["raio_max"] == pytest.approx(P.roda.raio_max)
    assert dados["veiculo"]["entre_eixos_L"] == pytest.approx(P.veiculo.entre_eixos_L)
    assert dados["ambiente"]["escada"]["espelho_E"] == pytest.approx(P.ambiente.escada.espelho_E)
