#!/usr/bin/env python3
"""
Gera as malhas STL do rover a partir dos parâmetros mestres.

As malhas não são desenhadas à mão: a roda de raios curvos é construída pelo
**mesmo perfil paramétrico** que `simulador_python.geometria_escada` usa para
resolver a marcha e que `prototipo_3d/fisica.js` usa para o contato em tempo
real. Mudar `roda.raio_max` no YAML muda a física, o gêmeo digital 3D e a malha
que o Gazebo carrega.

    python3 ferramentas/gerar_malhas.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulador_python.config import P  # noqa: E402
from simulador_python import estrutura as estr  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "ros2_ws", "src", "rover_frugal_description", "meshes")


# ---------------------------------------------------------------------------
# Utilidades de malha
# ---------------------------------------------------------------------------
def fita_extrudada(externa: np.ndarray, interna: np.ndarray, largura: float) -> trimesh.Trimesh:
    """Sólido gerado por uma 'fita' 2D (curva externa + interna) extrudada em Z.

    `externa` e `interna` são poligonais (n,2) com o mesmo número de pontos,
    percorridas no mesmo sentido. Produz uma malha fechada (watertight):
    tampas inferior e superior + as duas paredes laterais + as duas pontas.
    """
    n = len(externa)
    assert len(interna) == n, "as duas bordas precisam ter o mesmo número de pontos"
    z0, z1 = -largura / 2.0, +largura / 2.0

    v = []
    v += [(p[0], p[1], z0) for p in externa]     # 0        .. n-1
    v += [(p[0], p[1], z0) for p in interna]     # n        .. 2n-1
    v += [(p[0], p[1], z1) for p in externa]     # 2n       .. 3n-1
    v += [(p[0], p[1], z1) for p in interna]     # 3n       .. 4n-1
    vertices = np.array(v, dtype=float)

    E0, I0, E1, I1 = 0, n, 2 * n, 3 * n
    faces = []
    for i in range(n - 1):
        # tampa inferior (normal -Z)
        faces += [[E0 + i, I0 + i, I0 + i + 1], [E0 + i, I0 + i + 1, E0 + i + 1]]
        # tampa superior (normal +Z)
        faces += [[E1 + i, E1 + i + 1, I1 + i + 1], [E1 + i, I1 + i + 1, I1 + i]]
        # parede externa
        faces += [[E0 + i, E0 + i + 1, E1 + i + 1], [E0 + i, E1 + i + 1, E1 + i]]
        # parede interna
        faces += [[I0 + i, I1 + i, I1 + i + 1], [I0 + i, I1 + i + 1, I0 + i + 1]]
    # tampas de ponta
    faces += [[E0, E1, I1], [E0, I1, I0]]
    faces += [[E0 + n - 1, I0 + n - 1, I1 + n - 1], [E0 + n - 1, I1 + n - 1, E1 + n - 1]]

    malha = trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=True)
    malha.fix_normals()
    return malha


def perfil_raio(amostras: int = 60):
    """Curva central de um raio curvo, no plano XY, e a espessura ao longo dela."""
    u = np.linspace(0.0, 1.0, amostras)
    r = P.roda.raio_cubo + u * (P.roda.raio_max - P.roda.raio_cubo)
    th = P.roda.sentido_curvatura * P.roda.varredura_rad * u ** P.roda.expoente_perfil
    espessura = P.roda.espessura_raiz + u * (P.roda.espessura_ponta - P.roda.espessura_raiz)
    return r, th, espessura


# ---------------------------------------------------------------------------
# Peças
# ---------------------------------------------------------------------------
def roda_raios_curvos() -> trimesh.Trimesh:
    """Roda completa: cubo + 3 raios curvos + aro elástico."""
    r, th, esp = perfil_raio()
    partes = []

    for s in range(P.roda.num_raios_N):
        base = s * 2.0 * np.pi / P.roda.num_raios_N
        ang = base + th
        externa = np.column_stack((r * np.cos(ang), r * np.sin(ang)))
        r_int = r - esp
        interna = np.column_stack((r_int * np.cos(ang), r_int * np.sin(ang)))
        partes.append(fita_extrudada(externa, interna, P.roda.largura_raio))

        # Pastilha de borracha na ponta do raio
        pastilha = trimesh.creation.box(
            extents=[P.roda.pastilha_borracha.espessura * 2.4, 0.026,
                     P.roda.largura_raio + 0.006])
        pastilha.apply_transform(trimesh.transformations.rotation_matrix(ang[-1], [0, 0, 1]))
        pastilha.apply_translation([r[-1] * np.cos(ang[-1]), r[-1] * np.sin(ang[-1]), 0.0])
        partes.append(pastilha)

    # Cubo: anel fino (não disco maciço — seria massa morta) + cubo central
    anel_cubo = trimesh.creation.annulus(r_min=P.roda.raio_cubo - 0.012,
                                         r_max=P.roda.raio_cubo,
                                         height=P.roda.largura_raio * 0.9)
    boss = trimesh.creation.annulus(r_min=0.008, r_max=0.020,
                                    height=P.roda.largura_raio * 1.5)
    partes += [anel_cubo, boss]

    # Três nervuras ligando o cubo central ao anel do cubo
    for s in range(P.roda.num_raios_N):
        ang = s * 2.0 * np.pi / P.roda.num_raios_N + np.pi / P.roda.num_raios_N
        nervura = trimesh.creation.box(
            extents=[P.roda.raio_cubo - 0.014, 0.010, P.roda.largura_raio * 0.9])
        nervura.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 0, 1]))
        nervura.apply_translation([np.cos(ang) * (P.roda.raio_cubo - 0.006) / 2,
                                   np.sin(ang) * (P.roda.raio_cubo - 0.006) / 2, 0.0])
        partes.append(nervura)

    return trimesh.util.concatenate(partes)


#: Espessura de parede do aro (câmara de ar de bicicleta ou anel TPU impresso oco)
PAREDE_ARO = 0.0015


def aro_elastico() -> trimesh.Trimesh:
    """Aro elástico externo — peça de OUTRO material (TPU 95A ou câmara de ar).

    A malha é o toro externo; a massa considera **parede fina**, não sólido:
    uma câmara de ar 20" pesa ~130 g, não 370 g.
    """
    return trimesh.creation.torus(major_radius=P.roda.raio_max - 0.009,
                                  minor_radius=0.009,
                                  major_sections=72, minor_sections=14)


def volume_efetivo(nome: str, malha: trimesh.Trimesh) -> float:
    """Volume de MATERIAL da peça: aplica preenchimento de impressão e paredes ocas.

    O volume geométrico da malha é o do sólido. A peça impressa tem preenchimento
    parcial (exceto onde a especificação exige 100%) e o aro é oco. Ignorar isso
    superestima a massa em mais de 60%.
    """
    v = float(malha.volume)
    if nome == "aro_elastico":
        # casca fina: área de superfície x espessura de parede
        return float(malha.area) * PAREDE_ARO
    if nome == "caixa_organizadora":
        return v * 0.06        # caixa comercial de PP, parede de ~1,5 mm
    return v * PREENCHIMENTO.get(nome, 0.6)


#: Fração de material efetivo por peça impressa (preenchimento médio ponderado).
#: Os raios e a lâmina da espiral exigem 100% (especificação de impressão);
#: cubos, mangas e juntas rodam com preenchimento parcial.
PREENCHIMENTO = {
    "roda_raios_curvos": 0.72,   # raios a 100%, cubo e nervuras a ~45%
    "espiral_csts": 0.80,        # lâmina a 100%, núcleo e anel a ~50%
    "manga_4ws": 0.55,
    "junta_vertice": 0.60,
}


def espiral_csts() -> trimesh.Trimesh:
    """Mola espiral plana do C-STS, com a geometria dimensionada."""
    c = P.csts
    voltas = c.comprimento_desenrolado_L / (np.pi * (c.raio_interno_espiral + c.raio_externo_espiral))
    t = np.linspace(0.0, 1.0, 220)
    raio = c.raio_interno_espiral + t * (c.raio_externo_espiral - c.raio_interno_espiral)
    ang = t * 2.0 * np.pi * voltas
    externa = np.column_stack((raio * np.cos(ang), raio * np.sin(ang)))
    r_int = raio - c.espessura_t
    interna = np.column_stack((r_int * np.cos(ang), r_int * np.sin(ang)))
    lamina = fita_extrudada(externa, interna, c.largura_b)

    nucleo = trimesh.creation.annulus(r_min=0.008, r_max=c.raio_interno_espiral,
                                      height=c.largura_b)
    anel = trimesh.creation.annulus(r_min=c.raio_externo_espiral,
                                    r_max=c.raio_externo_espiral + 0.006,
                                    height=c.largura_b)
    return trimesh.util.concatenate([lamina, nucleo, anel])


def manga_4ws() -> trimesh.Trimesh:
    """Manga de esterçamento: corpo, alojamento de rolamento e flange do motor."""
    corpo = trimesh.creation.box(extents=[0.055, 0.055, 0.10])
    corpo.apply_translation([0, 0, 0.05])
    eixo = trimesh.creation.cylinder(radius=0.011, height=0.075)
    eixo.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    flange = trimesh.creation.box(extents=[0.030, 0.048, 0.048])
    flange.apply_translation([0.030, 0, 0])
    return trimesh.util.concatenate([corpo, eixo, flange])


def junta_vertice() -> trimesh.Trimesh:
    """Junta split-clamp do vértice do V invertido (duas mangas em ângulo)."""
    b = estr.geometria_bracos()["FL"]
    d1 = b.abracadeira - b.vertice
    d2 = b.manga - b.vertice
    partes = [trimesh.creation.icosphere(subdivisions=2, radius=0.030)]
    for d in (d1, d2):
        d = d / np.linalg.norm(d)
        manga = trimesh.creation.annulus(r_min=0.0135, r_max=0.023, height=0.045)
        eixo_z = np.array([0.0, 0.0, 1.0])
        rot = trimesh.geometry.align_vectors(eixo_z, d)
        manga.apply_transform(rot)
        manga.apply_translation(d * 0.032)
        partes.append(manga)
    return trimesh.util.concatenate(partes)


def caixa_organizadora() -> trimesh.Trimesh:
    """Caixa de carga: casca aberta em cima, com paredes de 3 mm."""
    e = estr.envelope()
    largura = min(0.46, P.veiculo.bitola_W - 2 * P.roda.raio_max * 0.55)
    profundidade = min(0.38, P.veiculo.entre_eixos_L - 2 * P.roda.raio_max * 0.75)
    altura = P.veiculo.altura_caixa
    externa = trimesh.creation.box(extents=[largura, profundidade, altura])
    interna = trimesh.creation.box(extents=[largura - 0.006, profundidade - 0.006, altura])
    interna.apply_translation([0, 0, 0.006])
    try:
        casca = externa.difference(interna)
        if casca is None or casca.is_empty:
            raise ValueError
    except Exception:
        casca = externa           # sem motor booleano: caixa sólida serve de visual
    return casca


# ---------------------------------------------------------------------------
def gerar(destino: str = DESTINO) -> dict:
    os.makedirs(destino, exist_ok=True)
    pecas = {
        "roda_raios_curvos": roda_raios_curvos(),
        "aro_elastico": aro_elastico(),
        "espiral_csts": espiral_csts(),
        "manga_4ws": manga_4ws(),
        "junta_vertice": junta_vertice(),
        "caixa_organizadora": caixa_organizadora(),
    }
    # Materiais por peça, para reconciliar a massa com o arquivo mestre
    material = {
        "roda_raios_curvos": ("PETG", 1270.0),
        "espiral_csts": ("PETG", 1270.0),
        "manga_4ws": ("PETG", 1270.0),
        "junta_vertice": ("PETG", 1270.0),
        "caixa_organizadora": ("PP", 900.0),
        "aro_elastico": ("TPU 95A", 1200.0),
    }
    relatorio = {}
    for nome, malha in pecas.items():
        caminho = os.path.join(destino, f"{nome}.stl")
        malha.export(caminho)
        mat, densidade = material[nome]
        massa = volume_efetivo(nome, malha) * densidade
        relatorio[nome] = {
            "arquivo": caminho,
            "triangulos": len(malha.faces),
            "volume_cm3": float(malha.volume) * 1e6,
            "material": mat,
            "massa_kg": massa,
            "estanque": bool(malha.is_watertight),
            "kb": os.path.getsize(caminho) / 1024,
        }
        print(f"  {nome:22s} {len(malha.faces):6d} tri  "
              f"sólido {float(malha.volume)*1e6:7.1f} cm³ → material "
              f"{volume_efetivo(nome, malha)*1e6:6.1f} cm³  {mat:8s} {massa*1000:6.0f} g  "
              f"{'estanque' if malha.is_watertight else 'ABERTA'}")
    return relatorio


def massa_conjunto_rodas(relatorio: dict | None = None) -> float:
    """Massa das 4 rodas completas, calculada a partir do volume das malhas.

    É o número que `massas.rodas_conjunto` no arquivo mestre precisa refletir —
    verificado por `testes/test_ros_urdf.py::test_massa_das_rodas_bate_com_as_malhas`.
    """
    if relatorio is None:
        pecas = {
            "roda_raios_curvos": roda_raios_curvos(),
            "espiral_csts": espiral_csts(),
            "aro_elastico": aro_elastico(),
        }
        dens = {"roda_raios_curvos": 1270.0, "espiral_csts": 1270.0, "aro_elastico": 1200.0}
        return 4.0 * sum(volume_efetivo(n, m) * dens[n] for n, m in pecas.items())
    return 4.0 * sum(relatorio[n]["massa_kg"]
                     for n in ("roda_raios_curvos", "espiral_csts", "aro_elastico"))


if __name__ == "__main__":
    print("Gerando malhas a partir de parametros_mestres.yaml:")
    rel = gerar()
    conjunto = massa_conjunto_rodas(rel)
    declarado = P.massas.rodas_conjunto
    print(f"\nMassa das 4 rodas completas (roda + C-STS + aro): {conjunto:.3f} kg")
    print(f"Declarada em massas.rodas_conjunto ..............: {declarado:.3f} kg "
          f"({100*(conjunto/declarado-1):+.1f}%)")
    if abs(conjunto / declarado - 1) > 0.20:
        print("  [!] Divergência acima de 20% — ajustar o arquivo mestre.")
    print(f"\n[OK] Malhas em {DESTINO}")
