#!/usr/bin/env python3
"""
Gera as figuras canônicas que a documentação referencia, em `Imagens/simulacao/`.

As figuras de trabalho (`--benchmark`) vão para `resultados/`, que é ignorado pelo
git. As figuras **citadas nos documentos** precisam estar versionadas para o
GitHub renderizá-las — é o que este script produz.

    python3 ferramentas/gerar_figuras.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulador_python.benchmark import executar_tudo  # noqa: E402

DESTINO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "Imagens", "simulacao")

if __name__ == "__main__":
    executar_tudo(DESTINO, verboso=True)
    print(f"\n[OK] Figuras da documentação em {DESTINO}")
