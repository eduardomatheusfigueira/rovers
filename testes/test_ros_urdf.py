"""
Verificação do pacote ROS 2 sem precisar de ROS instalado.

Expande o xacro com o pacote `xacro` (PyPI), carrega o URDF com `yourdfpy` e
confere que a descrição do robô corresponde ao arquivo mestre de parâmetros.
Todo desvio entre o que o simulador Python calcula e o que o Gazebo carregaria
aparece aqui, antes de virar um resultado de simulação errado.
"""

from __future__ import annotations

import math
import os
import re
import xml.dom.minidom as minidom

import numpy as np
import pytest

from simulador_python.config import P

xacro = pytest.importorskip("xacro", reason="pacote `xacro` não instalado")
yourdfpy = pytest.importorskip("yourdfpy", reason="pacote `yourdfpy` não instalado")

RAIZ = P.derivados.raiz_repositorio
SRC = os.path.join(RAIZ, "ros2_ws", "src")
DESCRICAO = os.path.join(SRC, "rover_frugal_description")
IDS = ("FL", "FR", "RL", "RR")


def _resolver_find(texto: str) -> str:
    """Substitui $(find pacote) pelo caminho do pacote no workspace."""
    return re.sub(r"\$\(find ([a-zA-Z0-9_]+)\)",
                  lambda m: os.path.join(SRC, m.group(1)), texto)


def _expandir(tmp_path, aro="true", ros2_control="false") -> str:
    for arq in ("rover_frugal.urdf.xacro", "sensores.gazebo.xacro"):
        origem = os.path.join(DESCRICAO, "urdf", arq)
        with open(origem, encoding="utf-8") as fh:
            (tmp_path / arq).write_text(_resolver_find(fh.read()), encoding="utf-8")
    doc = xacro.process_file(str(tmp_path / "rover_frugal.urdf.xacro"),
                             mappings={"aro_elastico": aro,
                                       "usar_ros2_control": ros2_control,
                                       "controladores": "/tmp/controladores.yaml"})
    destino = tmp_path / f"rover_{aro}.urdf"
    destino.write_text(doc.toprettyxml(indent="  "), encoding="utf-8")
    return str(destino)


@pytest.fixture(scope="module")
def urdf_com_aro(tmp_path_factory):
    return _expandir(tmp_path_factory.mktemp("aro"), aro="true")


@pytest.fixture(scope="module")
def urdf_sem_aro(tmp_path_factory):
    return _expandir(tmp_path_factory.mktemp("raios"), aro="false")


@pytest.fixture(scope="module")
def robo(urdf_com_aro):
    return yourdfpy.URDF.load(urdf_com_aro, load_meshes=False, build_scene_graph=True)


# =========================================================================
# Estrutura
# =========================================================================
def test_urdf_expande_nas_duas_variantes(urdf_com_aro, urdf_sem_aro):
    for caminho in (urdf_com_aro, urdf_sem_aro):
        assert os.path.getsize(caminho) > 5000


def test_cadeia_de_quatro_juntas_por_roda(robo):
    """suspensão → esterçamento → tração → C-STS, nessa ordem."""
    pais = {j.child: (j.parent, j.name, j.type) for j in robo.robot.joints}
    for w in IDS:
        pai, nome, tipo = pais[f"roda_{w}"]
        assert (pai, nome, tipo) == (f"cubo_{w}", f"csts_{w}", "revolute")
        pai, nome, tipo = pais[f"cubo_{w}"]
        assert (pai, nome, tipo) == (f"manga_{w}", f"tracao_{w}", "continuous")
        pai, nome, tipo = pais[f"manga_{w}"]
        assert (pai, nome, tipo) == (f"suporte_{w}", f"esterco_{w}", "revolute")
        pai, nome, tipo = pais[f"suporte_{w}"]
        assert (pai, nome, tipo) == ("base_link", f"susp_{w}", "prismatic")


def test_arvore_cinematica_sem_ciclo(robo):
    filhos = [j.child for j in robo.robot.joints]
    assert len(filhos) == len(set(filhos)), "um elo tem dois pais"
    assert len(robo.robot.links) == len(robo.robot.joints) + 1


# =========================================================================
# Coerência com o arquivo mestre
# =========================================================================
def test_massa_total_bate_com_o_arquivo_mestre(robo):
    massa = sum(l.inertial.mass for l in robo.robot.links if l.inertial is not None)
    assert massa == pytest.approx(P.massas.massa_total, rel=1e-6)


def test_inercias_positivas_definidas(robo):
    for elo in robo.robot.links:
        if elo.inertial is None:
            continue
        i = elo.inertial.inertia
        m = np.array([[i[0, 0], i[0, 1], i[0, 2]],
                      [i[0, 1], i[1, 1], i[1, 2]],
                      [i[0, 2], i[1, 2], i[2, 2]]])
        autovalores = np.linalg.eigvalsh(m)
        assert np.all(autovalores > 0), f"inércia não positiva-definida em {elo.name}"
        # Desigualdade triangular dos momentos principais
        a, b, c = sorted(autovalores)
        assert a + b >= c - 1e-12, f"momentos de inércia impossíveis em {elo.name}"


def test_geometria_das_rodas_bate_com_os_parametros(robo):
    robo.update_cfg(np.zeros(len(robo.actuated_joints)))
    esperado = {
        "FL": (+P.veiculo.entre_eixos_L / 2, +P.veiculo.bitola_W / 2),
        "FR": (+P.veiculo.entre_eixos_L / 2, -P.veiculo.bitola_W / 2),
        "RL": (-P.veiculo.entre_eixos_L / 2, +P.veiculo.bitola_W / 2),
        "RR": (-P.veiculo.entre_eixos_L / 2, -P.veiculo.bitola_W / 2),
    }
    for w, (x, y) in esperado.items():
        T = robo.get_transform(f"roda_{w}", "base_footprint")
        assert T[0, 3] == pytest.approx(x, abs=1e-6)
        assert T[1, 3] == pytest.approx(y, abs=1e-6)
        assert T[2, 3] == pytest.approx(P.roda.raio_max, abs=1e-6)


def test_limites_de_estercamento_batem_com_o_servo(robo):
    limite = math.radians(P.estercamento.angulo_maximo_deg)
    for j in robo.robot.joints:
        if j.name.startswith("esterco_"):
            assert j.limit.lower == pytest.approx(-limite)
            assert j.limit.upper == pytest.approx(+limite)
            assert j.limit.effort == pytest.approx(P.estercamento.torque_servo)


def test_curso_da_suspensao_bate_com_o_projeto(robo):
    for j in robo.robot.joints:
        if j.name.startswith("susp_"):
            curso = j.limit.upper - j.limit.lower
            assert curso == pytest.approx(P.suspensao_elastica.curso_maximo)
            assert j.limit.lower == pytest.approx(0.0), \
                "a junta zero deve ser a suspensão estendida"


def test_limite_do_csts_bate_com_o_batente(robo):
    for j in robo.robot.joints:
        if j.name.startswith("csts_"):
            assert j.limit.upper == pytest.approx(P.csts.deflexao_maxima_rad)


def test_eixo_de_giro_das_rodas_e_lateral(robo):
    for j in robo.robot.joints:
        if j.name.startswith(("tracao_", "csts_")):
            assert list(j.axis) == [0.0, 1.0, 0.0]
        if j.name.startswith(("esterco_", "susp_")):
            assert list(j.axis) == [0.0, 0.0, 1.0]


def test_torque_de_tracao_bate_com_o_motorredutor(robo):
    for j in robo.robot.joints:
        if j.name.startswith("tracao_"):
            assert j.limit.effort == pytest.approx(P.powertrain.torque_stall_saida, rel=1e-6)


# =========================================================================
# Colisão — o ponto mais delicado do modelo em Gazebo
# =========================================================================
def test_variante_com_aro_usa_cilindro(urdf_com_aro):
    robo = yourdfpy.URDF.load(urdf_com_aro, load_meshes=False)
    roda = next(l for l in robo.robot.links if l.name == "roda_FL")
    assert len(roda.collisions) == 1
    assert roda.collisions[0].geometry.cylinder is not None
    raio = roda.collisions[0].geometry.cylinder.radius
    # O raio é o NOMINAL: a complacência do aro está no contato (kp), não na
    # geometria — assim o afundamento responde à carga em vez de ser fixo.
    assert raio == pytest.approx(P.roda.raio_max)


def test_variante_sem_aro_usa_cadeia_de_esferas(urdf_sem_aro):
    """O casco convexo da malha é um disco: colisão precisa ser por primitivas."""
    robo = yourdfpy.URDF.load(urdf_sem_aro, load_meshes=False)
    roda = next(l for l in robo.robot.links if l.name == "roda_FL")
    assert len(roda.collisions) >= 3 * P.roda.num_raios_N
    assert all(c.geometry.sphere is not None for c in roda.collisions)
    # Nenhuma esfera pode ultrapassar o raio da roda
    for c in roda.collisions:
        x, y, z = c.origin[:3, 3]
        assert math.hypot(x, z) + c.geometry.sphere.radius <= P.roda.raio_max + 2e-3


def test_esferas_cobrem_o_raio_sem_buracos(urdf_sem_aro):
    """Esferas espaçadas demais deixariam o nariz do degrau 'passar entre' elas."""
    robo = yourdfpy.URDF.load(urdf_sem_aro, load_meshes=False)
    roda = next(l for l in robo.robot.links if l.name == "roda_FL")
    cadeia = [(c.origin[0, 3], c.origin[2, 3], c.geometry.sphere.radius)
              for c in roda.collisions if not (c.name or "").startswith("ponta_")]
    pontas = [(c.origin[0, 3], c.origin[2, 3], c.geometry.sphere.radius)
              for c in roda.collisions if (c.name or "").startswith("ponta_")]

    assert len(pontas) == P.roda.num_raios_N, "uma ponta nomeada por raio"
    por_raio = len(cadeia) // P.roda.num_raios_N
    for s in range(P.roda.num_raios_N):
        trecho = cadeia[s * por_raio:(s + 1) * por_raio]
        for (x1, z1, r1), (x2, z2, r2) in zip(trecho, trecho[1:]):
            assert math.hypot(x2 - x1, z2 - z1) <= r1 + r2 + 1e-9, \
                "lacuna entre esferas de colisão consecutivas"
        # A ponta precisa emendar na última esfera da cadeia daquele raio
        xf, zf, rf = trecho[-1]
        assert any(math.hypot(px - xf, pz - zf) <= rf + pr + 1e-9
                   for px, pz, pr in pontas), "ponta descolada da cadeia do raio"


def test_pontas_sao_colisoes_nomeadas_para_o_sensor_de_contato(urdf_sem_aro):
    """O sensor de contato referencia as pontas pelo nome: elas precisam existir."""
    robo = yourdfpy.URDF.load(urdf_sem_aro, load_meshes=False)
    xml = open(urdf_sem_aro, encoding="utf-8").read()
    for w in IDS:
        roda = next(l for l in robo.robot.links if l.name == f"roda_{w}")
        nomes = {c.name for c in roda.collisions if c.name}
        for i in range(P.roda.num_raios_N):
            assert f"ponta_{w}_{i}" in nomes
            assert f"<collision>ponta_{w}_{i}</collision>" in xml, \
                "sensor de contato não referencia a ponta"


def test_sensor_de_contato_existe_nas_duas_variantes(urdf_com_aro, urdf_sem_aro):
    for caminho in (urdf_com_aro, urdf_sem_aro):
        xml = open(caminho, encoding="utf-8").read()
        for w in IDS:
            assert f'name="contato_{w}" type="contact"' in xml
        assert "<topic>contatos</topic>" in xml


def test_odometria_de_verdade_terreno_publicada(urdf_com_aro):
    """Referência para medir o erro da odometria por encoder (ENS-15)."""
    xml = open(urdf_com_aro, encoding="utf-8").read()
    assert "gz-sim-odometry-publisher-system" in xml
    assert "<robot_base_frame>base_footprint</robot_base_frame>" in xml


def test_ventre_tem_colisao(robo):
    """Sem colisão no ventre a simulação não detecta encalhe no nariz do degrau."""
    base = next(l for l in robo.robot.links if l.name == "base_link")
    assert len(base.collisions) >= 1
    caixa = base.collisions[0].geometry.box
    assert caixa is not None
    fundo = base.collisions[0].origin[2, 3] - caixa.size[2] / 2 + P.roda.raio_max
    assert fundo == pytest.approx(P.veiculo.vao_livre_ventre, abs=1e-6)
    assert fundo > P.ambiente.escada.espelho_E


# =========================================================================
# Malhas
# =========================================================================
def test_malhas_referenciadas_existem(robo):
    for elo in robo.robot.links:
        for v in list(elo.visuals) + list(elo.collisions):
            if v.geometry.mesh is None:
                continue
            arquivo = v.geometry.mesh.filename.replace(
                "package://rover_frugal_description", DESCRICAO)
            assert os.path.exists(arquivo), f"malha ausente: {arquivo}"


def test_malhas_nao_tem_furos():
    """Sem arestas de borda: nenhum furo na superfície.

    Não se exige `is_watertight` porque as peças são compostas por sólidos que se
    interpenetram (raio + cubo + nervura). Ao voltar do STL, o `trimesh` funde
    vértices coincidentes e cria arestas não-manifold nessas junções — o que é
    irrelevante para o Gazebo e para o fatiador, que unem sólidos sobrepostos.
    O que importa é não haver FURO: aí sim o fatiador falharia.
    """
    trimesh = pytest.importorskip("trimesh")
    pasta = os.path.join(DESCRICAO, "meshes")
    for nome in sorted(os.listdir(pasta)):
        if not nome.endswith(".stl"):
            continue
        m = trimesh.load(os.path.join(pasta, nome))
        bordas = trimesh.grouping.group_rows(m.edges_sorted, require_count=1)
        assert len(bordas) == 0, f"{nome} tem {len(bordas)} arestas de borda (furo)"
        assert m.volume > 0, f"{nome} tem volume não positivo"


def test_massa_das_rodas_bate_com_as_malhas():
    """A massa declarada precisa refletir o volume real das peças geradas."""
    pytest.importorskip("trimesh")
    import sys
    sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))
    import gerar_malhas
    calculada = gerar_malhas.massa_conjunto_rodas()
    assert calculada == pytest.approx(P.massas.rodas_conjunto, rel=0.20)


# =========================================================================
# Mundos do Gazebo
# =========================================================================
@pytest.fixture(scope="module")
def mundos():
    pasta = os.path.join(SRC, "rover_frugal_gazebo", "worlds")
    return {n: minidom.parse(os.path.join(pasta, n))
            for n in sorted(os.listdir(pasta)) if n.endswith(".sdf")}


def test_mundos_sao_xml_valido(mundos):
    assert len(mundos) >= 3
    for nome, doc in mundos.items():
        assert doc.getElementsByTagName("world"), nome
        assert doc.getElementsByTagName("model"), nome


def test_escada_do_mundo_e_a_escada_do_projeto(mundos):
    """A escada simulada precisa ser a mesma que dimensiona a roda."""
    doc = mundos["percurso_parquetec.sdf"]
    alturas = []
    for modelo in doc.getElementsByTagName("model"):
        nome = modelo.getAttribute("name")
        if nome.startswith("degrau_") and not nome.endswith("patamar"):
            caixa = modelo.getElementsByTagName("size")[0].firstChild.data.split()
            alturas.append(float(caixa[2]))
            assert float(caixa[0]) == pytest.approx(P.ambiente.escada.piso_P), \
                "o piso do degrau simulado difere do piso de projeto"
    assert len(alturas) == P.ambiente.escada.num_degraus_lance
    # A escada nasce sobre o patamar da rampa: o que precisa bater é o ESPELHO,
    # isto é, a diferença de altura entre degraus consecutivos.
    for h1, h2 in zip(sorted(alturas), sorted(alturas)[1:]):
        assert h2 - h1 == pytest.approx(P.ambiente.escada.espelho_E, abs=1e-6)


def test_mundo_molhado_usa_o_atrito_reduzido(mundos):
    texto = mundos["escada_molhada.sdf"].toxml()
    assert f"<mu>{P.ambiente.piso.mu_borracha_concreto_molhado}</mu>" in texto
    seco = mundos["bancada_degrau.sdf"].toxml()
    assert f"<mu>{P.ambiente.piso.mu_borracha_concreto}</mu>" in seco


def test_passo_de_integracao_resolve_o_contato(mundos):
    """dt precisa ser pequeno o bastante para a rigidez de contato adotada."""
    for nome, doc in mundos.items():
        passo = float(doc.getElementsByTagName("max_step_size")[0].firstChild.data)
        m_nao_suspensa = P.massas.rodas_conjunto / 4.0
        # A frequência natural mais alta do contato é a da variante SEM aro
        # (pastilha de borracha sobre raio rígido).
        omega = math.sqrt(1.0e5 / m_nao_suspensa)
        assert omega * passo < 0.5, f"{nome}: passo de {passo} s é grande demais"
