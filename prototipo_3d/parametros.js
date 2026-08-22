// =============================================================================
//  ARQUIVO GERADO AUTOMATICAMENTE — NÃO EDITAR À MÃO
//  Origem: 00_Especificacao_Mestre/parametros_mestres.yaml
//  Gerador: ferramentas/gerar_parametros_js.py
//
//  Todo número de engenharia do protótipo 3D vem daqui. Para mudar a geometria
//  do rover, edite o YAML e rode novamente o gerador.
// =============================================================================

export const PARAMETROS = {
    "meta": {
        "projeto": "Rover Frugal 4WD/4WS — UGV de Inovação Frugal para Logística Predial",
        "revisao": "R2",
        "data_revisao": "2026-08-22",
        "variante_ativa": "v2_sincrona",
        "descricao_revisao": "R2 consolida a auditoria técnica (00_Especificacao_Mestre/02_Auditoria_Tecnica.md), corrige o dimensionamento da roda pela condição de marcha síncrona de raios, unifica massas, raios e contagem de raios entre documentos e código, e corrige a classificação cinemática de Siegwart (δm=1, δs=2, δM=3).\n",
        "variantes_disponiveis": [
            "v1_legado",
            "v2_sincrona",
            "v3_degrau_reduzido"
        ],
        "descricao_variante": "Variante ativa (R2). Roda Φ400 mm com 3 raios satisfaz a condição D = 2·r_max·sin(π/N) para o degrau de referência, e o entre-eixos é travado em 2 passos de degrau para sincronizar os eixos na escada.\n"
    },
    "ambiente": {
        "escada": {
            "espelho_E": 0.17,
            "piso_P": 0.3,
            "largura": 1.2,
            "num_degraus_lance": 8,
            "blondel_2E_mais_P": 0.64,
            "passo_D": 0.34481879299133333,
            "inclinacao_rad": 0.5155490074589791,
            "inclinacao_deg": 29.538782259558104
        },
        "meio_fio": {
            "altura_tipica": 0.12,
            "altura_maxima": 0.15
        },
        "piso": {
            "mu_borracha_concreto": 0.85,
            "mu_borracha_concreto_molhado": 0.55,
            "mu_borracha_marmore_polido": 0.4,
            "crr_asfalto": 0.03,
            "crr_grama": 0.11
        },
        "porta_estreita": 0.8,
        "corredor_estreito": 0.9
    },
    "veiculo": {
        "entre_eixos_L": 0.69,
        "bitola_W": 0.6,
        "fator_fase_escada_k": 2,
        "altura_cg_chassi": 0.28,
        "altura_cg_carga": 0.225,
        "altura_caixa": 0.25,
        "altura_fixacao_pendular": 0.357,
        "vao_livre_ventre": 0.19,
        "folga_ventre_medida": 0.079,
        "braco_pendular": 0.09276834862385314,
        "amortecimento_pendular": 4.5,
        "peso_total_N": 85.51398799999998,
        "altura_cg_total": 0.26423165137614685,
        "lf": 0.345,
        "lr": 0.345,
        "angulo_tombamento_long_deg": 52.55189909337403,
        "angulo_tombamento_lat_deg": 48.62729874121516,
        "pendulo_estavel": true
    },
    "massas": {
        "chassi_pvc": 1.3,
        "rodas_conjunto": 1.8,
        "tracao_conjunto": 0.9,
        "estercamento_conjunto": 0.45,
        "eletronica_potencia": 0.55,
        "bateria": 0.62,
        "caixa_organizadora": 0.6,
        "carga_util_nominal": 2.5,
        "carga_util_maxima": 3.0,
        "massa_seca": 6.22,
        "massa_total": 8.719999999999999,
        "massa_total_maxima": 9.219999999999999
    },
    "roda": {
        "num_raios_N": 3,
        "raio_max": 0.21,
        "raio_cubo": 0.07,
        "raio_curvatura_arco": 0.189,
        "largura_raio": 0.024,
        "espessura_raiz": 0.01,
        "espessura_ponta": 0.007,
        "varredura_rad": 1.35,
        "expoente_perfil": 0.85,
        "sentido_curvatura": 1,
        "pastilha_borracha": {
            "espessura": 0.008,
            "mu": 0.85
        },
        "material": "PETG",
        "densidade_material": 1270,
        "passo_angular_rad": 2.0943951023931953,
        "alcance_nariz_a_nariz": 0.3637306695894642,
        "raio_sincrono_exigido": 0.19908122295518815,
        "marcha_sincrona": true,
        "folga_sincronismo": 0.018911876598130872,
        "raio_medio_rolamento": 0.14
    },
    "aro_elastico": {
        "obrigatorio": true,
        "tipo": "câmara de ar de bicicleta 20\" (frugal) ou anel TPU 95A impresso",
        "rigidez_radial": 3500.0,
        "curso_colapso": 0.025,
        "massa_por_roda": 0.09,
        "forca_colapso_local": 90.0
    },
    "csts": {
        "modulo_young_pla": 3500000000.0,
        "modulo_young_petg": 2100000000.0,
        "material": "PETG",
        "largura_b": 0.03,
        "espessura_t": 0.00971,
        "comprimento_desenrolado_L": 0.386,
        "raio_interno_espiral": 0.02,
        "raio_externo_espiral": 0.062,
        "torque_projeto": 5.4,
        "deflexao_projeto_deg": 30.0,
        "kt_projeto": 10.31,
        "kt_empirico": 0.547,
        "fator_correcao_empirico": 0.828,
        "amortecimento_ct": 0.08,
        "deflexao_maxima_deg": 35.0,
        "inercia_roda": 0.0125,
        "modulo_young": 2100000000.0,
        "kt_teorico": 12.451729812823835,
        "deflexao_maxima_rad": 0.6108652381980153
    },
    "suspensao_elastica": {
        "elasticos_por_perna": 8,
        "rigidez_por_elastico": 125.0,
        "amortecimento_por_roda": 25.0,
        "curso_maximo": 0.09,
        "afundamento_estatico": 0.022,
        "pre_tensao_relativa": 0.2,
        "batente_deg": 25.0,
        "rigidez_por_roda": 1000.0
    },
    "powertrain": {
        "motor": {
            "tensao_nominal": 12.0,
            "kv_rpm_por_volt": 1000.0,
            "resistencia_armadura": 1.1,
            "corrente_vazio": 0.35,
            "torque_stall_rotor": 0.0265,
            "inercia_rotor": 1.2e-06,
            "kt_nm_por_a": 0.009549296585513721,
            "corrente_stall": 10.909090909090908,
            "torque_stall_calc": 0.10083189076431079
        },
        "reducao": 172.0,
        "eficiencia_reducao": 0.72,
        "num_motores": 4,
        "limite_corrente_driver": 20.0,
        "torque_stall_saida": 12.487021352252249,
        "rpm_vazio_saida": 69.76744186046511,
        "omega_vazio_saida": 7.306029426953007
    },
    "estercamento": {
        "torque_servo": 2.45,
        "velocidade_servo": 5.24,
        "angulo_maximo_deg": 55.0,
        "taxa_maxima_deg_s": 120.0,
        "tempo_reconfiguracao_modo": 0.75
    },
    "energia": {
        "quimica": "LiFePO4",
        "celulas_serie": 4,
        "celulas_paralelo": 2,
        "capacidade_celula_ah": 3.0,
        "tensao_nominal_celula": 3.2,
        "tensao_cheia_celula": 3.65,
        "tensao_corte_celula": 2.8,
        "resistencia_interna_celula": 0.025,
        "reserva_operacional": 0.2,
        "consumo_eletronica_w": 6.5,
        "tensao_nominal_pack": 12.8,
        "tensao_cheia_pack": 14.6,
        "tensao_corte_pack": 11.2,
        "capacidade_ah": 6.0,
        "energia_wh": 76.80000000000001,
        "energia_util_wh": 61.44000000000001,
        "resistencia_interna_pack": 0.05
    },
    "cinematica": {
        "grau_mobilidade_dm": 1,
        "grau_dirigibilidade_ds": 2,
        "grau_manobrabilidade_dM": 3,
        "holonomico": false,
        "velocidade_maxima": 1.2,
        "velocidade_escada": 0.25,
        "aceleracao_maxima": 0.5,
        "grau_manobrabilidade_calc": 3
    },
    "controle": {
        "frequencia_malha_hz": 200,
        "frequencia_telemetria_hz": 20,
        "timeout_failsafe_ms": 300,
        "pitch_critico_plano_deg": 35.0,
        "pitch_critico_escada_deg": 52.0,
        "roll_critico_deg": 30.0,
        "limite_choque_carga_g": 2.0,
        "arfagem_esperada_escada_deg": 43.0
    },
    "kpi": {
        "carga_util_kg": {
            "meta": 3.0,
            "minimo": 2.5
        },
        "degrau_transponivel_m": {
            "meta": 0.17,
            "minimo": 0.15
        },
        "velocidade_plano_ms": {
            "meta": 1.0,
            "minimo": 0.5
        },
        "choque_carga_g": {
            "meta": 1.5,
            "maximo": 2.5
        },
        "autonomia_min": {
            "meta": 45.0,
            "minimo": 30.0
        },
        "alcance_link_m": {
            "meta": 300.0,
            "minimo": 150.0
        },
        "troca_peca_min": {
            "meta": 10.0,
            "maximo": 15.0
        },
        "custo_material_usd": {
            "meta": 1000.0,
            "maximo": 1000.0
        },
        "margem_torque": {
            "meta": 2.0,
            "minimo": 1.5
        },
        "margem_tombamento_deg": {
            "meta": 15.0,
            "minimo": 10.0
        }
    }
};

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
