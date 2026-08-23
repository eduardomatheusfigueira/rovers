# 00. Parâmetros Mestres do Projeto

> **DOCUMENTO GERADO AUTOMATICAMENTE** — não editar à mão.
> Fonte: [`parametros_mestres.yaml`](parametros_mestres.yaml) ·
> Gerador: [`ferramentas/gerar_documentacao.py`](../ferramentas/gerar_documentacao.py) ·
> Regerar: `python3 ferramentas/gerar_documentacao.py`

| | |
| :--- | :--- |
| Revisão | **R2** (2026-08-22) |
| Variante ativa | **v2_sincrona** |
| Variantes disponíveis | `v1_legado`, `v2_sincrona`, `v3_degrau_reduzido` |
| Fonte da revisão | `parametros_mestres.yaml` (2026-08-22) |

Variante ativa (R2). Roda Φ400 mm com 3 raios satisfaz a condição D = 2·r_max·sin(π/N) para o degrau de referência, e o entre-eixos é travado em 2 passos de degrau para sincronizar os eixos na escada.

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
Variante ativa .............. v2_sincrona
Massa total (nominal) ....... 10.03 kg  (98.4 N)
Entre-eixos x bitola ........ 690 x 600 mm
Altura do CG ................ 266 mm
Tombamento long. / lat. ..... 52.3° / 48.4°
Escada de referência ........ E=170 mm, P=300 mm, 2E+P=64.0 cm, passo D=344.8 mm, 29.5°
Roda ........................ N=3 raios, r_max=210 mm (Φ420 mm), r_cubo=70 mm
Alcance nariz-a-nariz ....... 363.7 mm (exigido 344.8 mm) -> SÍNCRONA
C-STS ....................... kt_projeto=12.30 N·m/rad (artigo: 0.55 N·m/rad em outra escala)
Torque de stall por roda .... 12.49 N·m (redução 1:172)
Pack de bateria ............. 4S2P LiFePO4, 6.0 Ah, 77 Wh (61 Wh úteis)
Cinemática (Siegwart) ....... δm=1, δs=2, δM=3 (holonômico: não)
```

---

## 3. Verificações automáticas de coerência

| Verificação | Resultado |
| :--- | :--- |
| Blondel 2E + P na faixa NBR 9050 (0,63–0,65 m) | 0.640 m — ✔ |
| Marcha síncrona: D ≤ 2·r_max·sin(π/N) | 344.8 ≤ 363.7 mm — ✔ |
| Entre-eixos travado em fase (L = k·D) | 0.690 = 2·0.3448 — ✔ |
| Vão livre do ventre > espelho do degrau | 190 > 170 mm — ✔ |
| Pêndulo estável (CG abaixo da fixação) | braço = 91 mm — ✔ |
| δM = δm + δs | 3 = 1 + 2 — ✔ |
| Margem de tombamento na escada ≥ KPI | 22.8° ≥ 10° — ✔ |
| Atrito exigido na escada < disponível (seco) | 0.72 < 0.85 — ✔ |

Essas verificações são executadas como testes em `testes/test_parametros.py`.

---

## 4. Tabela completa de parâmetros

### meta

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `projeto` | Rover Frugal 4WD/4WS — UGV de Inovação Frugal para Logística Predial |  |
| `revisao` | R2 |  |
| `data_revisao` | 2026-08-22 |  |
| `variante_ativa` | v2_sincrona |  |
| `descricao_revisao` | R2 consolida a auditoria técnica (00_Especificacao_Mestre/02_Auditoria_Tecnica.md), corrige o dimensionamento da roda pela condição de marcha síncrona de raios, unifica massas, raios e contagem de raios entre documentos e código, e corrige a classificação cinemática de Siegwart (δm=1, δs=2, δM=3).
 |  |
| `variantes_disponiveis` | v1_legado, v2_sincrona, v3_degrau_reduzido |  |
| `descricao_variante` | Variante ativa (R2). Roda Φ400 mm com 3 raios satisfaz a condição D = 2·r_max·sin(π/N) para o degrau de referência, e o entre-eixos é travado em 2 passos de degrau para sincronizar os eixos na escada.
 |  |

### ambiente

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `porta_estreita` | 0.8 |  |
| `corredor_estreito` | 0.9 |  |

#### ambiente · escada

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `espelho_E` | 0.17 | m |
| `piso_P` | 0.3 | m |
| `largura` | 1.2 |  |
| `num_degraus_lance` | 8 |  |
| `blondel_2E_mais_P` | 0.64 |  |
| `passo_D` | 0.3448 | m |
| `inclinacao_rad` | 0.5155 |  |
| `inclinacao_deg` | 29.54 |  |

#### ambiente · meio_fio

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `altura_tipica` | 0.12 |  |
| `altura_maxima` | 0.15 |  |

#### ambiente · piso

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `mu_borracha_concreto` | 0.85 |  |
| `mu_borracha_concreto_molhado` | 0.55 |  |
| `mu_borracha_marmore_polido` | 0.4 |  |
| `crr_asfalto` | 0.03 |  |
| `crr_grama` | 0.11 |  |

### veiculo

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `entre_eixos_L` | 0.69 | m |
| `bitola_W` | 0.6 | m |
| `fator_fase_escada_k` | 2 |  |
| `altura_cg_chassi` | 0.28 |  |
| `altura_cg_carga` | 0.225 |  |
| `altura_caixa` | 0.25 |  |
| `altura_fixacao_pendular` | 0.357 |  |
| `vao_livre_ventre` | 0.19 |  |
| `folga_ventre_medida` | 0.079 |  |
| `braco_pendular` | 0.09071 |  |
| `amortecimento_pendular` | 4.5 |  |
| `peso_total_N` | 98.36 | N |
| `altura_cg_total` | 0.2663 |  |
| `lf` | 0.345 |  |
| `lr` | 0.345 |  |
| `angulo_tombamento_long_deg` | 52.34 |  |
| `angulo_tombamento_lat_deg` | 48.41 |  |
| `pendulo_estavel` | sim |  |

### massas

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `chassi_pvc` | 1.3 |  |
| `rodas_conjunto` | 2.55 |  |
| `tracao_conjunto` | 0.92 |  |
| `estercamento_conjunto` | 0.85 |  |
| `eletronica_potencia` | 0.55 |  |
| `bateria` | 0.76 |  |
| `caixa_organizadora` | 0.6 |  |
| `carga_util_nominal` | 2.5 |  |
| `carga_util_maxima` | 3 |  |
| `massa_seca` | 7.53 |  |
| `massa_total` | 10.03 | kg |
| `massa_total_maxima` | 10.53 |  |

### roda

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `num_raios_N` | 3 |  |
| `raio_max` | 0.21 | m |
| `raio_cubo` | 0.07 | m |
| `raio_curvatura_arco` | 0.189 |  |
| `largura_raio` | 0.024 |  |
| `espessura_raiz` | 0.01 |  |
| `espessura_ponta` | 0.007 |  |
| `varredura_rad` | 1.35 |  |
| `expoente_perfil` | 0.85 |  |
| `sentido_curvatura` | 1 |  |
| `material` | PETG |  |
| `densidade_material` | 1270 |  |
| `passo_angular_rad` | 2.094 |  |
| `alcance_nariz_a_nariz` | 0.3637 |  |
| `raio_sincrono_exigido` | 0.1991 |  |
| `marcha_sincrona` | sim |  |
| `folga_sincronismo` | 0.01891 |  |
| `raio_medio_rolamento` | 0.14 |  |

#### roda · pastilha_borracha

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `espessura` | 0.008 |  |
| `mu` | 0.85 |  |

### aro_elastico

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `obrigatorio` | sim |  |
| `tipo` | câmara de ar de bicicleta 20" (frugal) ou anel TPU 95A impresso |  |
| `rigidez_radial` | 3500 |  |
| `curso_colapso` | 0.025 |  |
| `massa_por_roda` | 0.09 |  |
| `forca_colapso_local` | 90 |  |

### csts

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `modulo_young_pla` | 3.500e+09 |  |
| `modulo_young_petg` | 2.100e+09 |  |
| `material` | PETG |  |
| `largura_b` | 0.03 |  |
| `espessura_t` | 0.0103 |  |
| `comprimento_desenrolado_L` | 0.386 |  |
| `raio_interno_espiral` | 0.02 |  |
| `raio_externo_espiral` | 0.062 |  |
| `torque_projeto` | 6.44 | N·m |
| `deflexao_projeto_deg` | 30 |  |
| `kt_projeto` | 12.3 | N·m/rad |
| `kt_empirico` | 0.547 |  |
| `fator_correcao_empirico` | 0.828 |  |
| `amortecimento_ct` | 0.08 |  |
| `deflexao_maxima_deg` | 35 |  |
| `inercia_roda` | 0.0125 |  |
| `modulo_young` | 2.100e+09 |  |
| `kt_teorico` | 14.86 |  |
| `deflexao_maxima_rad` | 0.6109 |  |

### suspensao_elastica

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `elasticos_por_perna` | 8 |  |
| `rigidez_por_elastico` | 125 |  |
| `amortecimento_por_roda` | 25 |  |
| `curso_maximo` | 0.09 |  |
| `afundamento_estatico` | 0.022 |  |
| `pre_tensao_relativa` | 0.2 |  |
| `batente_deg` | 25 |  |
| `rigidez_por_roda` | 1000 |  |

### powertrain

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `reducao` | 172 |  |
| `eficiencia_reducao` | 0.72 |  |
| `num_motores` | 4 |  |
| `limite_corrente_driver` | 20 |  |
| `torque_stall_saida` | 12.49 |  |
| `rpm_vazio_saida` | 69.77 |  |
| `omega_vazio_saida` | 7.306 |  |

#### powertrain · motor

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `tensao_nominal` | 12 |  |
| `kv_rpm_por_volt` | 1000 |  |
| `resistencia_armadura` | 1.1 |  |
| `corrente_vazio` | 0.35 |  |
| `torque_stall_rotor` | 0.0265 |  |
| `inercia_rotor` | 1.200e-06 |  |
| `kt_nm_por_a` | 0.009549 |  |
| `corrente_stall` | 10.91 |  |
| `torque_stall_calc` | 0.1008 |  |

### estercamento

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `torque_servo` | 2.45 |  |
| `velocidade_servo` | 5.24 |  |
| `angulo_maximo_deg` | 55 |  |
| `taxa_maxima_deg_s` | 120 |  |
| `tempo_reconfiguracao_modo` | 0.75 |  |

### energia

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `quimica` | LiFePO4 |  |
| `celulas_serie` | 4 |  |
| `celulas_paralelo` | 2 |  |
| `capacidade_celula_ah` | 3 |  |
| `tensao_nominal_celula` | 3.2 |  |
| `tensao_cheia_celula` | 3.65 |  |
| `tensao_corte_celula` | 2.8 |  |
| `resistencia_interna_celula` | 0.025 |  |
| `reserva_operacional` | 0.2 |  |
| `consumo_eletronica_w` | 6.5 |  |
| `tensao_nominal_pack` | 12.8 |  |
| `tensao_cheia_pack` | 14.6 |  |
| `tensao_corte_pack` | 11.2 |  |
| `capacidade_ah` | 6 |  |
| `energia_wh` | 76.8 |  |
| `energia_util_wh` | 61.44 |  |
| `resistencia_interna_pack` | 0.05 |  |

### cinematica

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `grau_mobilidade_dm` | 1 |  |
| `grau_dirigibilidade_ds` | 2 |  |
| `grau_manobrabilidade_dM` | 3 |  |
| `holonomico` | não |  |
| `velocidade_maxima` | 1.2 |  |
| `velocidade_escada` | 0.25 |  |
| `aceleracao_maxima` | 0.5 |  |
| `grau_manobrabilidade_calc` | 3 |  |

### controle

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `frequencia_malha_hz` | 200 |  |
| `frequencia_telemetria_hz` | 20 |  |
| `timeout_failsafe_ms` | 300 |  |
| `pitch_critico_plano_deg` | 35 |  |
| `pitch_critico_escada_deg` | 52 |  |
| `roll_critico_deg` | 30 |  |
| `limite_choque_carga_g` | 2 |  |
| `arfagem_esperada_escada_deg` | 43 |  |

### kpi

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |

#### kpi · carga_util_kg

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 3 |  |
| `minimo` | 2.5 |  |

#### kpi · degrau_transponivel_m

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 0.17 |  |
| `minimo` | 0.15 |  |

#### kpi · velocidade_plano_ms

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 1 |  |
| `minimo` | 0.5 |  |

#### kpi · choque_carga_g

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 1.5 |  |
| `maximo` | 2.5 |  |

#### kpi · autonomia_min

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 45 |  |
| `minimo` | 30 |  |

#### kpi · alcance_link_m

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 300 |  |
| `minimo` | 150 |  |

#### kpi · troca_peca_min

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 10 |  |
| `maximo` | 15 |  |

#### kpi · custo_material_usd

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 1000 |  |
| `maximo` | 1000 |  |

#### kpi · margem_torque

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 2 |  |
| `minimo` | 1.5 |  |

#### kpi · margem_tombamento_deg

| Parâmetro | Valor | Unid. |
| :--- | ---: | :--- |
| `meta` | 15 |  |
| `minimo` | 10 |  |
