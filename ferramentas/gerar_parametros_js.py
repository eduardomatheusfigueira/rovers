#!/usr/bin/env python3
"""
Gera `prototipo_3d/parametros.js` a partir do arquivo mestre de parâmetros.

O protótipo 3D deixa de ter números escritos no código: ele importa exatamente
os mesmos valores que o simulador Python e a documentação usam. Rodar:

    python3 ferramentas/gerar_parametros_js.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulador_python import config as cfgmod  # noqa: E402
from simulador_python import estrutura as estr  # noqa: E402

CABECALHO = """// =============================================================================
//  ARQUIVO GERADO AUTOMATICAMENTE — NÃO EDITAR À MÃO
//  Origem: 00_Especificacao_Mestre/parametros_mestres.yaml
//  Gerador: ferramentas/gerar_parametros_js.py
//
//  Todo número de engenharia do protótipo 3D vem daqui. Para mudar a geometria
//  do rover, edite o YAML e rode novamente o gerador.
// =============================================================================

"""

RODAPE = """
/** Converte o referencial canônico (x frente, y esquerda) para o do Three.js
 *  (X direita, Y cima, Z ré). */
export function paraCena(xFrente, yEsquerda) {
    return { x: -yEsquerda, z: -xFrente };
}

/** Posições das quatro rodas no referencial da cena. */
export const POSICOES_RODAS = (() => {
    const L = PARAMETROS.veiculo.entre_eixos_L, W = PARAMETROS.veiculo.bitola_W;
    return {
        FL: { x: -W / 2, z: -L / 2 },
        FR: { x: +W / 2, z: -L / 2 },
        RL: { x: -W / 2, z: +L / 2 },
        RR: { x: +W / 2, z: +L / 2 },
    };
})();

export const IDS_RODAS = ['FL', 'FR', 'RL', 'RR'];
"""


def _limpar(obj):
    """Remove chaves internas e converte tipos numpy para JSON."""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _limpar(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [_limpar(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def gerar(destino: str = None) -> str:
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    destino = destino or os.path.join(raiz, "prototipo_3d", "parametros.js")
    dados = _limpar(dict(cfgmod.P))
    dados.pop("derivados", None)

    bracos = {
        wid: {
            "abracadeira": list(map(float, b.abracadeira)),
            "vertice": list(map(float, b.vertice)),
            "manga": list(map(float, b.manga)),
            "eixo": list(map(float, b.eixo)),
            "haste_superior": b.haste_superior,
            "haste_inferior": b.haste_inferior,
        }
        for wid, b in estr.geometria_bracos().items()
    }
    dados["estrutura"] = {
        "bracos": bracos,
        "envelope": _limpar(estr.envelope()),
        "lista_de_corte": estr.lista_de_corte(),
    }

    corpo = json.dumps(dados, indent=4, ensure_ascii=False, sort_keys=False)
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(CABECALHO)
        fh.write(f"export const PARAMETROS = {corpo};\n")
        fh.write(RODAPE)
    print(f"[OK] {destino} ({os.path.getsize(destino)} bytes)")
    return destino


if __name__ == "__main__":
    gerar()
