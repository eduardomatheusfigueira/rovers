#!/usr/bin/env python3
"""
Gera `rover_frugal_description/config/parametros.yaml` — a ponte entre o arquivo
mestre de parâmetros e o URDF/xacro.

Por que existe: o xacro é **escrito à mão** (é o artefato nativo de ROS e precisa
ser legível), mas não contém nenhum número. Ele carrega este YAML com
`xacro.load_yaml` e monta o robô a partir dele. Assim a cadeia continua sendo:

    parametros_mestres.yaml → parametros.yaml → rover_frugal.urdf.xacro → URDF/SDF

Além dos escalares, este gerador resolve o que o xacro não deveria calcular:
distribuição de massa por elo, tensores de inércia e a **cadeia de esferas de
colisão** que representa os raios curvos (ver `03_Simulacao/05`, §4).

    python3 ferramentas/gerar_ros_config.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulador_python import estrutura as estr  # noqa: E402
from simulador_python.config import P  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACOTE = os.path.join(RAIZ, "ros2_ws", "src", "rover_frugal_description")
DESTINO = os.path.join(PACOTE, "config", "parametros.yaml")
DESTINO_CTRL = os.path.join(RAIZ, "ros2_ws", "src", "rover_frugal_control",
                            "config", "controladores.yaml")

IDS = ("FL", "FR", "RL", "RR")

#: Sobreposição mínima entre esferas consecutivas da cadeia de colisão.
#: Abaixo de 1,0 as esferas se tocam; 0,85 garante interpenetração e elimina
#: qualquer lacuna por onde o nariz do degrau pudesse atravessar.
FATOR_SOBREPOSICAO = 0.85


def inercia_caixa(massa: float, dx: float, dy: float, dz: float) -> dict:
    """Tensor de inércia de um paralelepípedo homogêneo."""
    return {
        "ixx": massa * (dy ** 2 + dz ** 2) / 12.0,
        "iyy": massa * (dx ** 2 + dz ** 2) / 12.0,
        "izz": massa * (dx ** 2 + dy ** 2) / 12.0,
        "ixy": 0.0, "ixz": 0.0, "iyz": 0.0,
    }


def inercia_roda(massa: float, izz_giro: float) -> dict:
    """Roda fina: momento de giro medido, os outros dois pela metade (disco)."""
    return {
        "ixx": izz_giro / 2.0, "iyy": izz_giro, "izz": izz_giro / 2.0,
        "ixy": 0.0, "ixz": 0.0, "iyz": 0.0,
    }


def esferas_colisao_raios() -> list:
    """Cadeia de esferas ao longo dos raios curvos, no referencial da roda.

    O casco convexo da malha da roda é um DISCO — usar `<mesh>` como colisão
    apagaria justamente a geometria de raios que o projeto depende. Por isso a
    colisão é composta por primitivas: uma cadeia de esferas segue a linha média
    de cada raio, com uma esfera maior na ponta representando a pastilha de
    borracha.

    Devolve [x, z, raio] já no REFERENCIAL DO ELO da roda (eixo de giro = y),
    para a roda do lado esquerdo. O lado direito é espelhado no xacro invertindo
    o sinal de z — é o que mantém a quiralidade dos raios curvos coerente nos
    dois lados do veículo.
    """
    r0, r1 = P.roda.raio_cubo, P.roda.raio_max
    esferas = []
    for s in range(P.roda.num_raios_N):
        base = s * 2.0 * np.pi / P.roda.num_raios_N

        def ponto(u: float):
            raio = r0 + u * (r1 - r0)
            ang = (base + P.roda.sentido_curvatura * P.roda.varredura_rad
                   * u ** P.roda.expoente_perfil)
            espessura = (P.roda.espessura_raiz
                         + u * (P.roda.espessura_ponta - P.roda.espessura_raiz))
            # malha (x, y) -> elo (x, -y): rotação de -90° em torno de X
            return (raio * np.cos(ang), -raio * np.sin(ang), espessura / 2.0 + 0.001)

        # Colocação ADAPTATIVA: uma esfera nova só é aceita quando ainda houver
        # sobreposição com a anterior. Esferas espaçadas demais deixam o nariz do
        # degrau "passar entre elas" e a roda atravessa a quina.
        u = 0.0
        anterior = ponto(0.0)
        esferas.append(list(anterior))
        while u < 1.0:
            passo = 1.0e-3
            candidato = anterior
            while u < 1.0:
                u = min(1.0, u + passo)
                candidato = ponto(u)
                d = np.hypot(candidato[0] - anterior[0], candidato[1] - anterior[1])
                if d >= 0.85 * (candidato[2] + anterior[2]):
                    break
            esferas.append(list(candidato))
            anterior = candidato

        # Pastilha de borracha na ponta: esfera maior, tangente a r_max por fora
        r_pastilha = P.roda.pastilha_borracha.espessura + 0.006
        ang = base + P.roda.sentido_curvatura * P.roda.varredura_rad
        centro = r1 - r_pastilha
        esferas[-1] = [float(centro * np.cos(ang)), float(-centro * np.sin(ang)),
                       float(r_pastilha)]
    return [[float(a), float(b), float(c)] for a, b, c in esferas]


def gerar(destino: str = DESTINO) -> str:
    os.makedirs(os.path.dirname(destino), exist_ok=True)

    v, r, sus, csts = P.veiculo, P.roda, P.suspensao_elastica, P.csts
    env = estr.envelope()
    bracos = estr.geometria_bracos()

    # --- distribuição de massa por elo -----------------------------------
    m_roda = P.massas.rodas_conjunto / 4.0
    m_cubo = P.massas.tracao_conjunto / 4.0            # motorredutor
    m_manga = P.massas.estercamento_conjunto / 4.0     # servo + manga impressa
    m_suporte = 0.030                                  # suporte deslizante da suspensão
    m_base = P.massas.massa_total - 4.0 * (m_roda + m_cubo + m_manga + m_suporte)

    largura_caixa = min(0.46, v.bitola_W - 2 * r.raio_max * 0.55)
    profundidade_caixa = min(0.38, v.entre_eixos_L - 2 * r.raio_max * 0.75)

    dados = {
        "_gerado_por": "ferramentas/gerar_ros_config.py",
        "_fonte": "00_Especificacao_Mestre/parametros_mestres.yaml",
        "_aviso": "ARQUIVO GERADO — não editar à mão.",
        "revisao": P.meta.revisao,

        "roda": {
            "raio_max": r.raio_max,
            "raio_cubo": r.raio_cubo,
            "largura": r.largura_raio,
            "num_raios": r.num_raios_N,
            # Com o aro montado a colisão é um cilindro no raio NOMINAL, e a
            # complacência do aro entra como rigidez DE CONTATO (kp). Assar a
            # deflexão no raio e ainda usar contato rígido contaria a mesma
            # flexibilidade duas vezes — e, pior, fixaria o afundamento num
            # valor único, independente da carga.
            "raio_com_aro": r.raio_max,
            "largura_com_aro": r.largura_raio + 0.010,
            "afundamento_aro_nominal": float(min(
                v.peso_total_N / 4.0 / P.aro_elastico.rigidez_radial,
                P.aro_elastico.curso_colapso)),
        },

        "veiculo": {
            "entre_eixos": v.entre_eixos_L,
            "bitola": v.bitola_W,
            "vao_livre": v.vao_livre_ventre,
            "altura_cg": v.altura_cg_chassi,
            "offset_cg_eixo": v.altura_cg_chassi - r.raio_max,
            "largura_caixa": largura_caixa,
            "profundidade_caixa": profundidade_caixa,
            "altura_caixa": v.altura_caixa,
            "altura_fixacao": v.altura_fixacao_pendular,
        },

        "envelope": {k: float(x) if not isinstance(x, bool) else x for k, x in env.items()},

        "massas": {
            "base": float(m_base),
            "suporte": float(m_suporte),
            "manga": float(m_manga),
            "cubo": float(m_cubo),
            "roda": float(m_roda),
            "total": float(P.massas.massa_total),
        },

        "inercias": {
            "base": {k: float(x) for k, x in inercia_caixa(
                m_base, largura_caixa, profundidade_caixa, v.altura_caixa).items()},
            "suporte": {k: float(x) for k, x in inercia_caixa(
                m_suporte, 0.05, 0.05, 0.05).items()},
            "manga": {k: float(x) for k, x in inercia_caixa(
                m_manga, 0.06, 0.06, 0.10).items()},
            "cubo": {k: float(x) for k, x in inercia_caixa(
                m_cubo, 0.06, 0.06, 0.06).items()},
            "roda": {k: float(x) for k, x in inercia_roda(m_roda, csts.inercia_roda).items()},
        },

        "juntas": {
            "suspensao": {
                "curso": sus.curso_maximo,
                # A junta zero é a suspensão TOTALMENTE ESTENDIDA (roda pendurada);
                # sob o peso próprio ela assenta no afundamento estático.
                "limite_inferior": 0.0,
                "limite_superior": sus.curso_maximo,
                "rigidez": sus.rigidez_por_roda,
                "amortecimento": sus.amortecimento_por_roda,
                "afundamento_estatico": sus.afundamento_estatico,
                "esforco_maximo": float(sus.rigidez_por_roda * sus.curso_maximo * 1.5),
                "velocidade_maxima": 1.0,
            },
            "estercamento": {
                "limite_rad": float(np.radians(P.estercamento.angulo_maximo_deg)),
                "esforco_maximo": P.estercamento.torque_servo,
                "velocidade_maxima": P.estercamento.velocidade_servo,
                "amortecimento": 0.05,
            },
            "tracao": {
                "esforco_maximo": float(P.powertrain.torque_stall_saida),
                "velocidade_maxima": float(P.powertrain.omega_vazio_saida),
                "amortecimento": 0.01,
                "atrito": 0.02,
            },
            "csts": {
                "limite_rad": csts.deflexao_maxima_rad,
                "rigidez": csts.kt_projeto,
                "amortecimento": csts.amortecimento_ct,
                "esforco_maximo": float(csts.kt_projeto * csts.deflexao_maxima_rad * 1.5),
                "velocidade_maxima": 20.0,
            },
        },

        "contato": {
            "mu_seco": P.ambiente.piso.mu_borracha_concreto,
            "mu_molhado": P.ambiente.piso.mu_borracha_concreto_molhado,
            "mu_polido": P.ambiente.piso.mu_borracha_marmore_polido,
            # kp É a rigidez radial do aro: sob W/4 = 24,6 N a roda afunda
            # 24,6/3500 = 7,0 mm, que é exatamente o afundamento previsto pelo
            # modelo analítico. Com o aro removido vale a rigidez da pastilha de
            # borracha sobre o raio de PETG.
            "kp_aro": float(P.aro_elastico.rigidez_radial),
            "kd_aro": 40.0,
            "kp_rigido": 1.0e5,
            "kd_rigido": 80.0,
        },

        "posicoes_rodas": {
            wid: {
                "x": float(bracos[wid].eixo[0] * 0 + (-1 if wid[0] == "F" else 1) * 0),
                "eixo": [float(-bracos[wid].eixo[2]),      # x_ros = frente = -z_cena
                         float(-bracos[wid].eixo[0]),      # y_ros = esquerda = -x_cena
                         float(bracos[wid].eixo[1])],
                "abracadeira": [float(-bracos[wid].abracadeira[2]),
                                float(-bracos[wid].abracadeira[0]),
                                float(bracos[wid].abracadeira[1])],
                "vertice": [float(-bracos[wid].vertice[2]),
                            float(-bracos[wid].vertice[0]),
                            float(bracos[wid].vertice[1])],
                "haste_superior": bracos[wid].haste_superior,
                "haste_inferior": bracos[wid].haste_inferior,
            }
            for wid in IDS
        },

        "colisao_raios": esferas_colisao_raios(),

        "controle": {
            "frequencia_hz": P.controle.frequencia_malha_hz,
            # A malha das juntas passivas precisa ser mais rápida que a maior
            # frequência natural do sistema: sqrt(k/m) da suspensão.
            "frequencia_passivas_hz": int(
                max(500, 20 * np.sqrt(sus.rigidez_por_roda / (P.massas.rodas_conjunto / 4)))),
            "velocidade_maxima": P.cinematica.velocidade_maxima,
            "velocidade_escada": P.cinematica.velocidade_escada,
            "pitch_critico_plano_deg": P.controle.pitch_critico_plano_deg,
            "pitch_critico_escada_deg": P.controle.pitch_critico_escada_deg,
            "roll_critico_deg": P.controle.roll_critico_deg,
            "timeout_failsafe_s": P.controle.timeout_failsafe_ms / 1000.0,
        },
    }

    with open(destino, "w", encoding="utf-8") as fh:
        fh.write("# ARQUIVO GERADO — não editar à mão.\n")
        fh.write("# Fonte: 00_Especificacao_Mestre/parametros_mestres.yaml\n")
        fh.write("# Gerador: ferramentas/gerar_ros_config.py\n\n")
        yaml.safe_dump(dados, fh, allow_unicode=True, sort_keys=False, default_flow_style=None)

    print(f"[OK] {destino}")
    print(f"     massa por elo: base {m_base:.3f} kg, roda {m_roda:.3f} kg, "
          f"cubo {m_cubo:.3f} kg, manga {m_manga:.3f} kg")
    print(f"     esferas de colisão por roda: {len(dados['colisao_raios'])}")
    print(f"     malha de juntas passivas: {dados['controle']['frequencia_passivas_hz']} Hz")
    return destino


def gerar_controladores(destino: str = DESTINO_CTRL) -> str:
    """Gera `controladores.yaml` do ros2_control e os parâmetros dos nós."""
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    sus = P.suspensao_elastica
    freq_passivas = int(max(500, 20 * np.sqrt(
        sus.rigidez_por_roda / (P.massas.rodas_conjunto / 4))))

    conf = {
        "controller_manager": {"ros__parameters": {
            # A taxa da malha é ditada pela junta mais rígida do sistema: com
            # integração explícita, ω·dt precisa ser bem menor que 1.
            "update_rate": max(1000, freq_passivas),
            "use_sim_time": True,
            "joint_state_broadcaster": {
                "type": "joint_state_broadcaster/JointStateBroadcaster"},
            "esterco_controller": {
                "type": "position_controllers/JointGroupPositionController"},
            "tracao_controller": {
                "type": "velocity_controllers/JointGroupVelocityController"},
            "passivas_controller": {
                "type": "effort_controllers/JointGroupEffortController"},
        }},
        "esterco_controller": {"ros__parameters": {
            "joints": [f"esterco_{w}" for w in IDS]}},
        "tracao_controller": {"ros__parameters": {
            "joints": [f"tracao_{w}" for w in IDS]}},
        "passivas_controller": {"ros__parameters": {
            "joints": [f"susp_{w}" for w in IDS] + [f"csts_{w}" for w in IDS]}},
        "cinematica_4ws": {"ros__parameters": {
            "entre_eixos": float(P.veiculo.entre_eixos_L),
            "bitola": float(P.veiculo.bitola_W),
            "raio_roda": float(P.roda.raio_max),
            "limite_estercamento_rad": float(np.radians(P.estercamento.angulo_maximo_deg)),
            "velocidade_servo_rad_s": float(P.estercamento.velocidade_servo),
            "velocidade_maxima": float(P.cinematica.velocidade_maxima),
            "velocidade_escada": float(P.cinematica.velocidade_escada),
            "frequencia_hz": float(P.controle.frequencia_malha_hz),
            "timeout_cmd_vel_s": float(P.controle.timeout_failsafe_ms / 1000.0),
            "use_sim_time": True}},
        "molas_passivas": {"ros__parameters": {
            "rigidez_suspensao": float(sus.rigidez_por_roda),
            "amortecimento_suspensao": float(sus.amortecimento_por_roda),
            "curso_suspensao": float(sus.curso_maximo),
            "rigidez_csts": float(P.csts.kt_projeto),
            "amortecimento_csts": float(P.csts.amortecimento_ct),
            "limite_csts_rad": float(P.csts.deflexao_maxima_rad),
            "frequencia_hz": float(freq_passivas),
            "use_sim_time": True}},
        "supervisor": {"ros__parameters": {
            "pitch_critico_plano_deg": float(P.controle.pitch_critico_plano_deg),
            "pitch_critico_escada_deg": float(P.controle.pitch_critico_escada_deg),
            "roll_critico_deg": float(P.controle.roll_critico_deg),
            "timeout_failsafe_s": float(P.controle.timeout_failsafe_ms / 1000.0),
            "frequencia_hz": 100.0,
            "resistencia_motor": float(P.powertrain.motor.resistencia_armadura),
            "use_sim_time": True}},
    }

    with open(destino, "w", encoding="utf-8") as fh:
        fh.write("# ARQUIVO GERADO - nao editar a mao.\n")
        fh.write("# Fonte: 00_Especificacao_Mestre/parametros_mestres.yaml\n")
        fh.write("# Gerador: ferramentas/gerar_ros_config.py\n\n")
        yaml.safe_dump(conf, fh, sort_keys=False, allow_unicode=True)
    print(f"[OK] {destino}")
    print(f"     controller_manager a "
          f"{conf['controller_manager']['ros__parameters']['update_rate']} Hz, "
          f"molas passivas a {freq_passivas} Hz")
    return destino


if __name__ == "__main__":
    gerar()
    gerar_controladores()
