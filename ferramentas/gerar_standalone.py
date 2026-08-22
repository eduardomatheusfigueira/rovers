#!/usr/bin/env python3
"""
Gera `prototipo_3d_standalone.html`: um único arquivo, sem servidor e sem rede.

O repositório tinha DUAS cópias do protótipo — a modular em `prototipo_3d/` e uma
cópia manual em `prototipo_3d_standalone.html`. Elas divergiram. Agora a versão
standalone é BUILD, não fonte: este script embute CSS, módulos e a própria
biblioteca Three.js no HTML.

    python3 ferramentas/gerar_standalone.py
"""

from __future__ import annotations

import base64
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(RAIZ, "prototipo_3d")
DESTINO = os.path.join(RAIZ, "prototipo_3d_standalone.html")

MODULOS = ["parametros.js", "fisica.js", "terreno.js", "rover_model.js", "app.js"]
VENDOR = {
    "three": os.path.join(PROTO, "vendor", "three", "three.module.js"),
    "three/addons/controls/OrbitControls.js": os.path.join(PROTO, "vendor", "three",
                                                           "OrbitControls.js"),
}

AVISO = """<!--
  ===========================================================================
   ARQUIVO GERADO — NÃO EDITAR À MÃO
   Fonte: prototipo_3d/  ·  Gerador: ferramentas/gerar_standalone.py
   Reconstrua com:  python3 ferramentas/gerar_standalone.py
  ===========================================================================
-->
"""


def _blob(caminho: str) -> str:
    """Embute um módulo como data: URL para o import map."""
    with open(caminho, "r", encoding="utf-8") as fh:
        conteudo = fh.read()
    b64 = base64.b64encode(conteudo.encode("utf-8")).decode("ascii")
    return f"data:text/javascript;base64,{b64}"


def gerar() -> str:
    html = open(os.path.join(PROTO, "index.html"), encoding="utf-8").read()
    css = open(os.path.join(PROTO, "style.css"), encoding="utf-8").read()

    # 1. CSS inline
    html = html.replace('<link rel="stylesheet" href="style.css">',
                        f"<style>\n{css}\n</style>")

    # 2. Import map apontando para data: URLs do Three.js versionado
    mapa = ",\n".join(f'            "{nome}": "{_blob(caminho)}"'
                      for nome, caminho in VENDOR.items())

    # 3. Módulos do projeto, também como data: URLs (preservam os imports entre si)
    resolvidos: dict[str, str] = {}
    for nome in MODULOS:
        caminho = os.path.join(PROTO, nome)
        fonte = open(caminho, encoding="utf-8").read()
        for outro, url in resolvidos.items():
            fonte = fonte.replace(f"'./{outro}'", f"'{url}'")
            fonte = fonte.replace(f'"./{outro}"', f'"{url}"')
        b64 = base64.b64encode(fonte.encode("utf-8")).decode("ascii")
        resolvidos[nome] = f"data:text/javascript;base64,{b64}"

    html = re.sub(r'<script type="importmap">.*?</script>',
                  '<script type="importmap">\n    {\n        "imports": {\n'
                  + mapa + '\n        }\n    }\n    </script>',
                  html, flags=re.S)
    html = html.replace('<script type="module" src="app.js"></script>',
                        f'<script type="module" src="{resolvidos["app.js"]}"></script>')
    html = html.replace("<!DOCTYPE html>", "<!DOCTYPE html>\n" + AVISO)
    html = html.replace("<title>Gêmeo Digital",
                        "<title>[standalone] Gêmeo Digital")

    with open(DESTINO, "w", encoding="utf-8") as fh:
        fh.write(html)
    tamanho = os.path.getsize(DESTINO) / 1024
    print(f"[OK] {DESTINO} ({tamanho:.0f} KB) — abra com duplo clique, sem servidor.")
    return DESTINO


if __name__ == "__main__":
    sys.exit(0 if gerar() else 1)
