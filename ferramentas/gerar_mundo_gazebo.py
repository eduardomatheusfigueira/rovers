#!/usr/bin/env python3
"""
Gera os mundos SDF do Gazebo a partir dos parâmetros mestres.

A escadaria do mundo é construída com o **mesmo** espelho e piso que dimensionam
a roda. Não existe a possibilidade de simular uma escada diferente da que o
projeto declara — que é justamente o erro mais fácil de cometer num mundo
desenhado à mão.

Mundos gerados:
  percurso_parquetec.sdf   percurso completo de homologação (piso seco)
  escada_molhada.sdf       mesma escada com μ = 0,55 — a restrição operacional
                           de A-10 vira um cenário executável
  bancada_degrau.sdf       degrau isolado, para o ensaio de transposição

    python3 ferramentas/gerar_mundo_gazebo.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulador_python.config import P  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "ros2_ws", "src", "rover_frugal_gazebo", "worlds")


def caixa(nome, tamanho, pose, cor=(0.42, 0.45, 0.50), mu=0.85, estatico=True):
    sx, sy, sz = tamanho
    return f"""
    <model name="{nome}">
      <static>{'true' if estatico else 'false'}</static>
      <pose>{pose[0]:.4f} {pose[1]:.4f} {pose[2]:.4f} 0 0 0</pose>
      <link name="link">
        <collision name="colisao">
          <geometry><box><size>{sx:.4f} {sy:.4f} {sz:.4f}</size></box></geometry>
          <surface>
            <friction><ode><mu>{mu}</mu><mu2>{mu}</mu2></ode></friction>
            <contact><ode><kp>1e7</kp><kd>1e3</kd></ode></contact>
          </surface>
        </collision>
        <visual name="visual">
          <geometry><box><size>{sx:.4f} {sy:.4f} {sz:.4f}</size></box></geometry>
          <material>
            <ambient>{cor[0]} {cor[1]} {cor[2]} 1</ambient>
            <diffuse>{cor[0]} {cor[1]} {cor[2]} 1</diffuse>
          </material>
        </visual>
      </link>
    </model>"""


def marcador(nome, pose, cor):
    return f"""
    <model name="{nome}">
      <static>true</static>
      <pose>{pose[0]:.3f} {pose[1]:.3f} {pose[2]:.3f} 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><cylinder><radius>0.40</radius><length>0.004</length></cylinder></geometry>
          <material>
            <ambient>{cor} 0.6</ambient><diffuse>{cor} 0.6</diffuse>
            <emissive>{cor} 0.4</emissive>
          </material>
        </visual>
      </link>
    </model>"""


def escadaria(x0: float, mu: float, num_degraus: int, largura: float,
              base_y: float = 0.0, prefixo: str = "degrau") -> str:
    """Lance de escada subindo no sentido +x, cada degrau um bloco maciço."""
    E, Pp = P.ambiente.escada.espelho_E, P.ambiente.escada.piso_P
    partes = []
    for i in range(num_degraus):
        altura = base_y + (i + 1) * E
        centro_x = x0 + i * Pp + Pp / 2.0
        tom = 0.40 + 0.02 * (i % 3)
        partes.append(caixa(f"{prefixo}_{i:02d}", (Pp, largura, altura),
                            (centro_x, 0.0, altura / 2.0),
                            cor=(tom, tom + 0.03, tom + 0.08), mu=mu))
    patamar = base_y + num_degraus * E
    partes.append(caixa(f"{prefixo}_patamar", (4.0, largura + 1.2, patamar),
                        (x0 + num_degraus * Pp + 2.0, 0.0, patamar / 2.0),
                        cor=(0.38, 0.41, 0.46), mu=mu))
    return "".join(partes), patamar, x0 + num_degraus * Pp


CABECALHO = """<?xml version="1.0"?>
<!--
  ARQUIVO GERADO - nao editar a mao.
  Fonte:   00_Especificacao_Mestre/parametros_mestres.yaml
  Gerador: ferramentas/gerar_mundo_gazebo.py
-->
<sdf version="1.9">
  <world name="{nome}">

    <physics name="{motor}" type="{motor}">
      <max_step_size>{passo}</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-contact-system" name="gz::sim::systems::Contact"/>

    <gravity>0 0 -9.80665</gravity>
    <scene>
      <ambient>0.5 0.5 0.55 1</ambient>
      <background>0.06 0.08 0.12 1</background>
      <grid>false</grid>
      <shadows>true</shadows>
    </scene>

    <light type="directional" name="sol">
      <pose>0 0 12 0 0 0</pose>
      <diffuse>1.0 0.97 0.92 1</diffuse>
      <specular>0.25 0.25 0.25 1</specular>
      <direction>-0.4 0.3 -0.9</direction>
      <cast_shadows>true</cast_shadows>
    </light>

    <model name="piso">
      <static>true</static>
      <link name="link">
        <collision name="colisao">
          <geometry><plane><normal>0 0 1</normal><size>200 200</size></plane></geometry>
          <surface>
            <friction><ode><mu>{mu}</mu><mu2>{mu}</mu2></ode></friction>
          </surface>
        </collision>
        <visual name="visual">
          <geometry><plane><normal>0 0 1</normal><size>200 200</size></plane></geometry>
          <material>
            <ambient>0.16 0.19 0.24 1</ambient><diffuse>0.16 0.19 0.24 1</diffuse>
          </material>
        </visual>
      </link>
    </model>
"""

RODAPE = """
  </world>
</sdf>
"""


def mundo_percurso(mu: float, nome: str, passo: float = 0.001,
                   motor: str = "dart") -> str:
    esc = P.ambiente.escada
    partes = [CABECALHO.format(nome=nome, mu=mu, passo=passo, motor=motor)]

    # 1. Meio-fio entre via e calçada
    partes.append(caixa("meio_fio", (6.0, 8.0, P.ambiente.meio_fio.altura_tipica),
                        (7.0, 0.0, P.ambiente.meio_fio.altura_tipica / 2),
                        cor=(0.45, 0.46, 0.48), mu=mu))

    # 2. Rampa de acessibilidade, aproximada por degraus curtos (8%)
    base = P.ambiente.meio_fio.altura_tipica
    for i in range(12):
        h = base + 0.30 * (i + 1) / 12
        partes.append(caixa(f"rampa_{i:02d}", (0.32, 2.6, h),
                            (10.2 + i * 0.32, 0.0, h / 2),
                            cor=(0.30, 0.42, 0.35), mu=mu))
    topo_rampa = base + 0.30
    partes.append(caixa("patamar_rampa", (4.0, 2.6, topo_rampa),
                        (16.1, 0.0, topo_rampa / 2), cor=(0.40, 0.43, 0.47), mu=mu))

    # 3. Escadaria de Blondel
    x_escada = 18.2
    blocos, altura_topo, x_fim = escadaria(x_escada, mu, esc.num_degraus_lance,
                                           esc.largura, base_y=topo_rampa)
    partes.append(blocos)

    # 4. Porta estreita e corredor da T.I., no patamar superior
    vao = P.ambiente.porta_estreita
    corredor = P.ambiente.corredor_estreito
    x_porta = x_fim + 1.4
    for lado, sinal in (("esq", +1), ("dir", -1)):
        partes.append(caixa(f"parede_porta_{lado}", (0.20, 1.6, 2.0),
                            (x_porta, sinal * (vao / 2 + 0.8), altura_topo + 1.0),
                            cor=(0.22, 0.25, 0.30), mu=0.6))
        partes.append(caixa(f"parede_corredor_{lado}", (2.4, 0.15, 2.0),
                            (x_porta + 1.3, sinal * (corredor / 2 + 0.075),
                             altura_topo + 1.0),
                            cor=(0.22, 0.25, 0.30), mu=0.6))

    # 5. Marcadores da missão
    partes.append(marcador("ponto_base", (0.0, 0.0, 0.005), "1.0 0.63 0.0"))
    partes.append(marcador("ponto_coleta", (14.5, 0.0, topo_rampa + 0.005), "0.0 0.69 1.0"))
    partes.append(marcador("ponto_entrega", (x_porta + 2.2, 0.0, altura_topo + 0.005),
                           "0.0 0.85 0.47"))

    partes.append(RODAPE)
    return "".join(partes)


def mundo_bancada(mu: float, nome: str, passo: float = 0.0005) -> str:
    """Degrau isolado: o ensaio de transposição (ENS-05/ENS-06) em simulação."""
    esc = P.ambiente.escada
    partes = [CABECALHO.format(nome=nome, mu=mu, passo=passo, motor="dart")]
    blocos, _, _ = escadaria(2.0, mu, 4, esc.largura, prefixo="ensaio")
    partes.append(blocos)
    partes.append(caixa("meio_fio_ensaio", (1.0, 2.0, P.ambiente.meio_fio.altura_maxima),
                        (-3.0, 0.0, P.ambiente.meio_fio.altura_maxima / 2),
                        cor=(0.45, 0.46, 0.48), mu=mu))
    partes.append(marcador("largada", (0.2, 0.0, 0.005), "1.0 0.63 0.0"))
    partes.append(RODAPE)
    return "".join(partes)


def gerar(destino: str = DESTINO) -> dict:
    os.makedirs(destino, exist_ok=True)
    mu_seco = P.ambiente.piso.mu_borracha_concreto
    mu_molhado = P.ambiente.piso.mu_borracha_concreto_molhado

    mundos = {
        "percurso_parquetec.sdf": mundo_percurso(mu_seco, "percurso_parquetec"),
        "escada_molhada.sdf": mundo_bancada(mu_molhado, "escada_molhada"),
        "bancada_degrau.sdf": mundo_bancada(mu_seco, "bancada_degrau"),
    }
    for nome, conteudo in mundos.items():
        caminho = os.path.join(destino, nome)
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write(conteudo)
        print(f"  {nome:26s} {os.path.getsize(caminho)/1024:6.1f} KB")
    return mundos


if __name__ == "__main__":
    esc = P.ambiente.escada
    print(f"Gerando mundos com a escada do projeto "
          f"(E={esc.espelho_E*1000:.0f} mm, P={esc.piso_P*1000:.0f} mm, "
          f"{esc.num_degraus_lance} degraus):")
    gerar()
    print(f"\n[OK] Mundos em {DESTINO}")
