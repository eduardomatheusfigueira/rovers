"""
Geometria estrutural do chassi: pontos de junta e lista de corte dos tubos.

O roteiro de montagem de R1 mandava cortar hastes de 350 mm e 400 mm — cotas que
pertenciam a uma geometria de veículo que já não existe. Aqui os comprimentos são
**derivados** das posições de roda, da altura de fixação pendular e do vão livre,
de modo que mudar o diâmetro da roda no arquivo mestre muda a lista de corte.

Convenção: referencial da CENA (X para a direita, Y para cima, Z para a ré),
com origem no solo, sob o centro do veículo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from .config import P as PARAMS

IDS = ("FL", "FR", "RL", "RR")


@dataclass
class Braco:
    """Um dos quatro braços em V invertido."""

    id: str
    abracadeira: np.ndarray     # fixação no terço superior da caixa
    vertice: np.ndarray         # ápice do V (junta 3D)
    manga: np.ndarray           # topo da manga de esterçamento
    eixo: np.ndarray            # centro da roda

    @property
    def haste_superior(self) -> float:
        return float(np.linalg.norm(self.vertice - self.abracadeira))

    @property
    def haste_inferior(self) -> float:
        return float(np.linalg.norm(self.manga - self.vertice))

    @property
    def angulo_superior(self) -> float:
        """Ângulo da haste ascendente com a horizontal [graus]."""
        d = self.vertice - self.abracadeira
        return float(np.degrees(np.arctan2(d[1], np.hypot(d[0], d[2]))))

    @property
    def angulo_inferior(self) -> float:
        d = self.manga - self.vertice
        return float(np.degrees(np.arctan2(-d[1], np.hypot(d[0], d[2]))))


def geometria_bracos() -> Dict[str, Braco]:
    """Posições das juntas dos quatro braços, derivadas dos parâmetros mestres."""
    v, r = PARAMS.veiculo, PARAMS.roda
    meia_bitola = v.bitola_W / 2.0
    meio_eixo = v.entre_eixos_L / 2.0

    # Caixa organizadora: dimensões proporcionais ao vão entre as rodas,
    # deixando folga para o esterçamento das rodas dianteiras.
    largura_caixa = round(min(0.46, 2 * meia_bitola - 2 * r.raio_max * 0.55), 3)
    profundidade_caixa = round(min(0.38, 2 * meio_eixo - 2 * r.raio_max * 0.75), 3)

    bracos = {}
    for wid in IDS:
        sx = -1.0 if wid[1] == "L" else 1.0
        sz = -1.0 if wid[0] == "F" else 1.0

        abracadeira = np.array([sx * largura_caixa / 2.0,
                                v.altura_fixacao_pendular,
                                sz * profundidade_caixa / 2.0])
        eixo = np.array([sx * meia_bitola, r.raio_max, sz * meio_eixo])
        manga = eixo + np.array([0.0, PARAMS.suspensao_elastica.curso_maximo * 0.7, 0.0])

        # O vértice fica acima e por fora da abraçadeira, na direção da manga:
        # é essa triangulação que transforma flexão em esforço axial nos tubos.
        direcao = manga - abracadeira
        direcao_horizontal = np.array([direcao[0], 0.0, direcao[2]])
        vertice = (abracadeira
                   + 0.35 * direcao_horizontal
                   + np.array([0.0, 0.5 * r.raio_max, 0.0]))
        bracos[wid] = Braco(wid, abracadeira, vertice, manga, eixo)
    return bracos


def lista_de_corte() -> List[dict]:
    """Lista de corte dos tubos de PVC, com folga de encaixe nas juntas."""
    bracos = geometria_bracos()
    folga = 0.030      # 30 mm de tubo dentro de cada junta split-clamp
    ref = bracos["FL"]
    return [
        {"peca": "Haste superior (ascendente)", "qtd": 4,
         "comprimento_mm": round((ref.haste_superior + 2 * folga) * 1000),
         "angulo_deg": round(ref.angulo_superior, 1),
         "obs": "abraçadeira da caixa → vértice do V"},
        {"peca": "Haste inferior (descendente)", "qtd": 4,
         "comprimento_mm": round((ref.haste_inferior + 2 * folga) * 1000),
         "angulo_deg": round(ref.angulo_inferior, 1),
         "obs": "vértice do V → manga de esterçamento 4WS"},
    ]


def envelope() -> Dict[str, float]:
    """Envelope externo do veículo, para checar portas e corredores."""
    v, r = PARAMS.veiculo, PARAMS.roda
    largura = v.bitola_W + PARAMS.roda.largura_raio + 2 * 0.02
    comprimento = v.entre_eixos_L + 2 * r.raio_max
    altura = v.vao_livre_ventre + v.altura_caixa + 0.03
    return {
        "largura_m": largura,
        "comprimento_m": comprimento,
        "altura_m": altura,
        "passa_em_porta": bool(largura < PARAMS.ambiente.porta_estreita),
        "folga_na_porta_mm": (PARAMS.ambiente.porta_estreita - largura) * 1000,
        "passa_em_corredor": bool(largura < PARAMS.ambiente.corredor_estreito),
        "raio_de_giro_m": float(np.hypot(v.bitola_W / 2, v.entre_eixos_L / 2) + r.raio_max),
    }


def resumo() -> str:
    b = geometria_bracos()["FL"]
    e = envelope()
    linhas = [
        "Geometria estrutural derivada dos parâmetros mestres",
        f"  Haste superior ......... {b.haste_superior*1000:.0f} mm  ({b.angulo_superior:.0f}° acima da horizontal)",
        f"  Haste inferior ......... {b.haste_inferior*1000:.0f} mm  ({b.angulo_inferior:.0f}° abaixo da horizontal)",
        f"  Envelope (C x L x A) ... {e['comprimento_m']*1000:.0f} x {e['largura_m']*1000:.0f} x {e['altura_m']*1000:.0f} mm",
        f"  Passa em porta de {PARAMS.ambiente.porta_estreita*1000:.0f} mm ... "
        f"{'sim' if e['passa_em_porta'] else 'NÃO'} (folga {e['folga_na_porta_mm']:.0f} mm)",
        f"  Raio de giro no eixo ... {e['raio_de_giro_m']*1000:.0f} mm",
    ]
    linhas.append("\n  Lista de corte de tubos de PVC:")
    for item in lista_de_corte():
        linhas.append(f"    {item['qtd']}x {item['peca']:32s} {item['comprimento_mm']:4d} mm "
                      f"({item['angulo_deg']:+.1f}°)  {item['obs']}")
    return "\n".join(linhas)


if __name__ == "__main__":  # pragma: no cover
    print(resumo())
