#!/usr/bin/env python3
"""
Gera `00_Especificacao_Mestre/00_Parametros_Mestres.md` a partir do YAML mestre.

A tabela de parâmetros do projeto passa a ser artefato gerado: não existe mais
a possibilidade de a documentação divergir do simulador.

    python3 ferramentas/gerar_documentacao.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from simulador_python import config as cfgmod  # noqa: E402
from simulador_python.config import P  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "00_Especificacao_Mestre", "00_Parametros_Mestres.md")

UNIDADES = {
    "espelho_E": "m", "piso_P": "m", "passo_D": "m", "entre_eixos_L": "m",
    "bitola_W": "m", "raio_max": "m", "raio_cubo": "m", "massa_total": "kg",
    "peso_total_N": "N", "kt_projeto": "N·m/rad", "torque_projeto": "N·m",
}


def _fmt(v):
    if isinstance(v, bool):
        return "sim" if v else "não"
    if isinstance(v, float):
        if abs(v) >= 1e5 or (abs(v) < 1e-3 and v != 0):
            return f"{v:.3e}"
        return f"{v:.4g}"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def _secao(titulo: str, dados: dict, nivel: int = 3) -> str:
    linhas = [f"{'#' * nivel} {titulo}\n",
              "| Parâmetro | Valor | Unid. |", "| :--- | ---: | :--- |"]
    for chave, valor in dados.items():
        if isinstance(valor, dict):
            continue
        linhas.append(f"| `{chave}` | {_fmt(valor)} | {UNIDADES.get(chave, '')} |")
    linhas.append("")
    for chave, valor in dados.items():
        if isinstance(valor, dict):
            linhas.append(_secao(f"{titulo} · {chave}", valor, nivel + 1))
    return "\n".join(linhas)


def gerar() -> str:
    esc, roda = P.ambiente.escada, P.roda
    # Sem carimbo de data/hora: o arquivo precisa ser DETERMINÍSTICO para que a
    # verificação de sincronia da integração contínua funcione.
    cabecalho = f"""# 00. Parâmetros Mestres do Projeto

> **DOCUMENTO GERADO AUTOMATICAMENTE** — não editar à mão.
> Fonte: [`parametros_mestres.yaml`](parametros_mestres.yaml) ·
> Gerador: [`ferramentas/gerar_documentacao.py`](../ferramentas/gerar_documentacao.py) ·
> Regerar: `python3 ferramentas/gerar_documentacao.py`

| | |
| :--- | :--- |
| Revisão | **{P.meta.revisao}** ({P.meta.data_revisao}) |
| Variante ativa | **{P.meta.variante_ativa}** |
| Variantes disponíveis | {", ".join(f"`{v}`" for v in P.meta.variantes_disponiveis)} |
| Fonte da revisão | `parametros_mestres.yaml` ({P.meta.data_revisao}) |

{P.meta.descricao_variante.strip()}

---

## 1. Por que este arquivo existe

Antes da revisão R2 o mesmo número aparecia com valores diferentes em lugares
diferentes: a roda era Φ240 mm em um documento, Φ300 mm em outro e r = 0,10 m no
cálculo de torque; a massa era 7,5 kg no simulador e 10 kg no dimensionamento
elétrico; a roda tinha 3 raios em cinco documentos e 4 no catálogo de peças. Cada
divergência dessas é um erro de projeto esperando a fase de fabricação para
aparecer.

A regra passa a ser: **nenhum número de engenharia é digitado duas vezes.** Todo
valor vive em `parametros_mestres.yaml` e é consumido por:

```
parametros_mestres.yaml
   │
   ├─ simulador_python/config.py ──── simulador, benchmarks e Relatório de Engenharia
   ├─ prototipo_3d/parametros.js ──── gêmeo digital 3D  (gerar_parametros_js.py)
   └─ 00_Parametros_Mestres.md ────── esta tabela        (gerar_documentacao.py)
```

---

## 2. Resumo executivo da configuração

```
{cfgmod.resumo()}
```

---

## 3. Verificações automáticas de coerência

| Verificação | Resultado |
| :--- | :--- |
| Blondel 2E + P na faixa NBR 9050 (0,63–0,65 m) | {esc.blondel_2E_mais_P:.3f} m — {'✔' if 0.63 <= esc.blondel_2E_mais_P <= 0.65 else '✘'} |
| Marcha síncrona: D ≤ 2·r_max·sin(π/N) | {esc.passo_D*1000:.1f} ≤ {roda.alcance_nariz_a_nariz*1000:.1f} mm — {'✔' if roda.marcha_sincrona else '✘'} |
| Entre-eixos travado em fase (L = k·D) | {P.veiculo.entre_eixos_L:.3f} = {P.veiculo.fator_fase_escada_k}·{esc.passo_D:.4f} — {'✔' if abs(P.veiculo.entre_eixos_L - P.veiculo.fator_fase_escada_k*esc.passo_D) < 0.005 else '✘'} |
| Vão livre do ventre > espelho do degrau | {P.veiculo.vao_livre_ventre*1000:.0f} > {esc.espelho_E*1000:.0f} mm — {'✔' if P.veiculo.vao_livre_ventre > esc.espelho_E else '✘'} |
| Pêndulo estável (CG abaixo da fixação) | braço = {P.veiculo.braco_pendular*1000:.0f} mm — {'✔' if P.veiculo.pendulo_estavel else '✘'} |
| δM = δm + δs | {P.cinematica.grau_manobrabilidade_dM} = {P.cinematica.grau_mobilidade_dm} + {P.cinematica.grau_dirigibilidade_ds} — {'✔' if P.cinematica.grau_manobrabilidade_calc == P.cinematica.grau_manobrabilidade_dM else '✘'} |
| Margem de tombamento na escada ≥ KPI | {P.veiculo.angulo_tombamento_long_deg - esc.inclinacao_deg:.1f}° ≥ {P.kpi.margem_tombamento_deg.minimo:.0f}° — {'✔' if P.veiculo.angulo_tombamento_long_deg - esc.inclinacao_deg >= P.kpi.margem_tombamento_deg.minimo else '✘'} |
| Atrito exigido na escada < disponível (seco) | {np.tan(esc.inclinacao_rad)+0.15:.2f} < {P.ambiente.piso.mu_borracha_concreto:.2f} — {'✔' if np.tan(esc.inclinacao_rad)+0.15 < P.ambiente.piso.mu_borracha_concreto else '✘'} |

Essas verificações são executadas como testes em `testes/test_parametros.py`.

---

## 4. Tabela completa de parâmetros

"""
    corpo = []
    ordem = ["meta", "ambiente", "veiculo", "massas", "roda", "aro_elastico", "csts",
             "suspensao_elastica", "powertrain", "estercamento", "energia",
             "cinematica", "controle", "kpi"]
    for chave in ordem:
        if chave in P:
            corpo.append(_secao(chave, P[chave], nivel=3))

    texto = cabecalho + "\n".join(corpo)
    with open(DESTINO, "w", encoding="utf-8") as fh:
        fh.write(texto)
    print(f"[OK] {DESTINO} ({len(texto)} caracteres)")
    return DESTINO


if __name__ == "__main__":
    gerar()
