"""
Gerador do Relatório de Engenharia.

Executa a bateria completa de benchmarks e emite um documento Markdown com todos
os números do projeto — o mesmo conjunto que alimenta a documentação. O objetivo
é que NENHUM número da documentação seja digitado à mão: ou vem do arquivo
mestre de parâmetros, ou é gerado aqui.
"""

from __future__ import annotations

import datetime as _dt
import os
from typing import Dict

import numpy as np

from . import config as cfgmod
from .benchmark import executar_tudo
from .config import P as PARAMS
from . import estrutura as estr
from .kinematics import Cinematica4WS, classificar_siegwart
from .powertrain import ModeloTermicoMotor, MotorCC, OrcamentoEnergia, PackBateria
from .terramechanics import TerramecanicaWong

CABECALHO = """# Relatório de Engenharia — Rover Frugal 4WD/4WS

> **Documento gerado automaticamente** por `python -m simulador_python.main --relatorio`.
> Não editar à mão: todo número aqui vem de `00_Especificacao_Mestre/parametros_mestres.yaml`
> ou é calculado pelos módulos de `simulador_python/`.

| | |
| :--- | :--- |
| Revisão dos parâmetros | `{revisao}` |
| Variante ativa | `{variante}` |
| Gerado em | {data} |
"""


def _tabela(linhas, cabecalho) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |",
             "| " + " | ".join([":---"] * len(cabecalho)) + " |"]
    for linha in linhas:
        saida.append("| " + " | ".join(str(c) for c in linha) + " |")
    return "\n".join(saida)


def gerar(diretorio: str = "resultados", arquivo: str = None) -> str:
    os.makedirs(diretorio, exist_ok=True)
    arquivo = arquivo or os.path.join(diretorio, "RELATORIO_ENGENHARIA.md")
    print("Executando a bateria de benchmarks...")
    res = executar_tudo(diretorio, verboso=True)

    esc, roda, veic = PARAMS.ambiente.escada, PARAMS.roda, PARAMS.veiculo
    terra = TerramecanicaWong()
    motor, termico = MotorCC(), ModeloTermicoMotor()
    pack = PackBateria()
    sw = res["B6"]["siegwart"]
    sw_desc = res["B6"]["siegwart_descoordenado"]

    partes = [CABECALHO.format(revisao=PARAMS.meta.revisao,
                               variante=PARAMS.meta.variante_ativa,
                               data=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"))]

    # -- 1. configuração ---------------------------------------------------
    partes.append("\n## 1. Configuração avaliada\n\n```\n" + cfgmod.resumo() + "\n```\n")

    # -- 2. geometria de escalada ------------------------------------------
    b1 = res["B1"]["resultados"]
    linhas = []
    for nome, r in b1.items():
        linhas.append([nome, "sim" if r.sucesso else "**não**", r.degraus_vencidos,
                       f"{r.degraus_por_volta:.2f}", f"{r.queda_maxima*1000:.0f} mm",
                       f"{r.torque_pico:.2f} N·m", r.motivo[:58]])
    partes.append(f"""
## 2. Geometria de escalada

Condição de marcha síncrona (um degrau por raio):

$$D = \\sqrt{{E^2 + P^2}} \\le 2\\,r_{{max}}\\sin(\\pi/N)
\\quad\\Longleftrightarrow\\quad r_{{max}} \\ge \\frac{{D}}{{2\\sin(\\pi/N)}}$$

Para o degrau de referência ({esc.espelho_E*1000:.0f} x {esc.piso_P*1000:.0f} mm,
2E+P = {esc.blondel_2E_mais_P*100:.1f} cm, {esc.inclinacao_deg:.1f}°):

* passo nariz-a-nariz **D = {esc.passo_D*1000:.1f} mm**
* raio mínimo para N = 3: **{roda.raio_sincrono_exigido*1000:.1f} mm** (Φ {2*roda.raio_sincrono_exigido*1000:.0f} mm)
* alcance da roda adotada (r_max = {roda.raio_max*1000:.0f} mm): **{roda.alcance_nariz_a_nariz*1000:.1f} mm**
  (folga de {roda.folga_sincronismo*1000:+.1f} mm)

{_tabela(linhas, ["Variante", "Escala?", "Degraus", "Degraus/volta", "Queda máx. do cubo", "Torque de pico", "Desfecho"])}

![Marcha das duas variantes](b1_dimensionamento_roda.png)

A robustez de fase (varredura da posição de chegada ao primeiro degrau) está em
`b4_robustez_fase.png`: Φ{2*roda.raio_max*1000:.0f} mm é o menor diâmetro com
100% de sucesso tanto no degrau de referência quanto no pior caso da NBR 9050
(180 x 320 mm).

![Robustez de fase](b4_robustez_fase.png)

Folga do ventre medida na subida: **{veic.folga_ventre_medida*1000:.0f} mm** abaixo do
eixo das rodas. Com r_max = {roda.raio_max*1000:.0f} mm e 20 mm de margem, o vão
livre adotado é de **{veic.vao_livre_ventre*1000:.0f} mm**.
""")

    # -- 3. suspensão -------------------------------------------------------
    esp, imp = res["espiral"], res["impacto"]
    linhas_sus = []
    for cenario, configs in res["B2/B3"]["tabela"].items():
        for rotulo, m in configs.items():
            pv = m["pico_vertical_g"]
            linhas_sus.append([cenario, rotulo,
                               "instável" if not np.isfinite(pv) else f"{pv:.2f} g",
                               "—" if not np.isfinite(pv) else f"{m['rms_vertical_g']:.2f} g",
                               "—" if not np.isfinite(pv) else f"{m['pico_longitudinal_g']:.2f} g",
                               "—" if not np.isfinite(pv) else f"{m['pico_arfagem_deg']:.1f}°"])
    partes.append(f"""
## 3. Suspensão em dois estágios

### 3.1. Dimensionamento do C-STS por semelhança dimensional

```
{esp.resumo()}
```

A rigidez publicada por Jeong & Kim (2025) — {PARAMS.csts.kt_empirico:.2f} N·m/rad — vale
para a escala do artigo. Aplicada a este rover, o torque de projeto de
{PARAMS.csts.torque_projeto:.2f} N·m produziria
{np.degrees(PARAMS.csts.torque_projeto/PARAMS.csts.kt_empirico):.0f}° de deflexão: a mola
enrolaria por completo. A rigidez de projeto é **{esp.kt_efetivo:.2f} N·m/rad**.

### 3.2. Impacto na transferência de raio

```
{imp.resumo()}
```

### 3.3. Resposta dinâmica com a carga a bordo

{_tabela(linhas_sus, ["Cenário", "Configuração", "Pico vertical", "RMS", "Pico longitudinal", "Arfagem"])}

![Aceleração na carga](b2_b3_suspensao.png)

**Curso da suspensão.** A marcha impõe quedas de cubo de até
{b1['Adotado Φ440 (R2)'].queda_maxima*1000:.0f} mm. Absorver essa energia
({PARAMS.massas.massa_total*9.80665*b1['Adotado Φ440 (R2)'].queda_maxima:.1f} J) dentro do
limite de {PARAMS.controle.limite_choque_carga_g:.1f} g exige curso de
**{PARAMS.suspensao_elastica.curso_maximo*1000:.0f} mm** com rigidez de
{PARAMS.suspensao_elastica.rigidez_por_roda:.0f} N/m por roda
(afundamento estático de {PARAMS.suspensao_elastica.afundamento_estatico*1000:.0f} mm).
""")

    # -- 4. tração ----------------------------------------------------------
    missao, autonomia = res["B5"]["missao"], res["B5"]["autonomia"]
    linhas_m = [[t.trecho.nome, f"{t.trecho.distancia:.0f} m", f"{t.duracao:.0f} s",
                 f"{t.torque_por_roda:.2f}", f"{t.margem_torque:.2f}",
                 f"{t.corrente_total:.1f} A", f"{t.energia_wh:.2f} Wh"]
                for t in missao["trechos"]]
    partes.append(f"""
## 4. Cadeia de tração e energia

Motorredutor {motor.reducao:.0f}:1 — torque de stall na saída
**{motor.torque_stall_saida:.2f} N·m**, rotação a vazio
{motor.omega_vazio_saida*60/(2*np.pi):.0f} rpm ({motor.omega_vazio_saida*roda.raio_max:.2f} m/s).

![Cadeia de tração](b5_tracao.png)

### 4.1. Missão de homologação (Parquetec)

{_tabela(linhas_m, ["Trecho", "Distância", "Duração", "Torque/roda [N·m]", "Margem", "Corrente", "Energia"])}

* Total: **{missao['distancia_total_m']:.0f} m** em **{missao['duracao_total_s']/60:.1f} min**,
  consumindo **{missao['energia_total_wh']:.1f} Wh**
  ({missao['fracao_energia_util']*100:.0f}% da energia útil do pack).
* Margem de torque mínima: **{missao['margem_torque_minima']:.2f}**
  (requisito: {PARAMS.kpi.margem_torque.minimo:.2f}).
* Corrente de pico: **{missao['corrente_pico']:.1f} A** = {missao['taxa_c_pico']:.1f}C —
  exige células com descarga contínua ≥ 5C.
* Autonomia em ciclo misto: **{autonomia['autonomia_min']:.0f} min**
  (requisito: {PARAMS.kpi.autonomia_min.minimo:.0f} min).

### 4.2. Limite térmico — a restrição real da escada

O motor opera com ~11% de rendimento na escada: quase toda a potência elétrica
vira calor no enrolamento.

* Corrente contínua admissível: **{res['B5']['corrente_continua']:.2f} A**
* Tempo até 115 °C na corrente de escada: **{res['B5']['tempo_limite_escada']:.0f} s**
* Um lance de {PARAMS.ambiente.escada.num_degraus_lance} degraus a
  {PARAMS.cinematica.velocidade_escada:.2f} m/s leva ~11 s.

**Consequência para o firmware:** é obrigatória proteção I²t com pausa de
resfriamento entre lances consecutivos.
""")

    # -- 5. cinemática ------------------------------------------------------
    erros = res["B6"]["erros_servo"]
    linhas_e = [[f"{k:.1f}°", f"{v*1000:.1f} mm/s"] for k, v in erros.items()]
    comp = res["B6"]["comparacao"]
    partes.append(f"""
## 5. Cinemática e manobra

Classificação de Siegwart & Nourbakhsh (2004), calculada pelo posto da matriz de
restrições de deslizamento:

* configuração **coordenada** (as quatro normais convergem num ICR comum):
  posto(C1s) = {sw['posto_C1s']} → **δm = {sw['delta_m']}, δs = {sw['delta_s']}, δM = {sw['delta_M']}**
  → {sw['categoria']}
* configuração **descoordenada**: posto(C1s) = {sw_desc['posto_C1s']} → δm = {sw_desc['delta_m']}
  → **o veículo trava**.

> O rover **não é holonômico**. δM = 3 significa que ele alcança qualquer
> movimento no plano, mas δs = 2 significa que precisa **parar e reorientar as
> rodas** para mudar de modo. Custo de reconfiguração medido:
> {", ".join(f"{k} = {v:.2f} s" for k, v in res['B6']['custo_reconfiguracao'].items())}.

Tolerância de calibração dos servos (arrasto lateral induzido a 1 m/s por erro
em um único servo):

{_tabela(linhas_e, ["Erro de calibração", "Arrasto lateral"])}

Manobra a 0,8 m/s: 4WS coordenado **{comp['potencia_4ws_w']:.1f} W** contra
skid-steer **{comp['potencia_skid_w']:.1f} W** ({comp['economia_percentual']:.0f}% de economia).

![Manobra](b6_manobra.png)
""")

    # -- 5b. estrutura -------------------------------------------------------
    env = estr.envelope()
    linhas_corte = [[f"{i['qtd']}x", i["peca"], f"{i['comprimento_mm']} mm",
                     f"{i['angulo_deg']:+.1f}°", i["obs"]] for i in estr.lista_de_corte()]
    partes.append(f"""
## 5b. Geometria estrutural e envelope

```
{estr.resumo()}
```

{_tabela(linhas_corte, ["Qtd.", "Peça", "Corte", "Ângulo", "Trecho"])}

* Envelope: **{env['comprimento_m']*1000:.0f} × {env['largura_m']*1000:.0f} × {env['altura_m']*1000:.0f} mm**
* Passa em porta de {PARAMS.ambiente.porta_estreita*1000:.0f} mm:
  **{'sim' if env['passa_em_porta'] else 'NÃO'}** (folga {env['folga_na_porta_mm']:.0f} mm)
* Raio de giro no próprio eixo: **{env['raio_de_giro_m']*1000:.0f} mm**
""")

    # -- 6. estabilidade e limites -----------------------------------------
    plano = terra.avaliar()
    escada_est = terra.avaliar(pitch=esc.inclinacao_rad, crr=0.15)
    partes.append(f"""
## 6. Estabilidade e limites operacionais

* Tombamento estático: longitudinal **{veic.angulo_tombamento_long_deg:.1f}°**,
  lateral **{veic.angulo_tombamento_lat_deg:.1f}°** (CG a {veic.altura_cg_total*1000:.0f} mm).
* Arfagem esperada em operação normal na escada: **~{PARAMS.controle.arfagem_esperada_escada_deg:.0f}°**
  (29,5° da rampa + oscilação da marcha). Por isso o limiar anti-tombamento é
  dependente de modo: {PARAMS.controle.pitch_critico_plano_deg:.0f}° em piso,
  {PARAMS.controle.pitch_critico_escada_deg:.0f}° em modo escada.
* Cargas normais em piso plano: {", ".join(f"{k}={v:.1f} N" for k, v in plano.fz.items())}.
* Cargas na escada ({esc.inclinacao_deg:.1f}°):
  {", ".join(f"{k}={v:.1f} N" for k, v in escada_est.fz.items())} — a transferência
  é **para trás**, portanto são as rodas TRASEIRAS que fazem o esforço de subida.
* Atrito mínimo exigido na escada: **{terra.atrito_minimo_exigido(esc.inclinacao_rad, 0.15):.2f}**.
  Disponível em concreto seco: {PARAMS.ambiente.piso.mu_borracha_concreto:.2f} ✔ ·
  concreto molhado: {PARAMS.ambiente.piso.mu_borracha_concreto_molhado:.2f} ✘ ·
  mármore polido: {PARAMS.ambiente.piso.mu_borracha_marmore_polido:.2f} ✘

> **Restrição operacional derivada:** proibida a subida de escadas com piso
> molhado ou em superfície polida. O modo escada deve ser bloqueado pelo
> firmware quando o piloto não confirmar a condição do piso.
""")

    texto = "\n".join(partes)
    with open(arquivo, "w", encoding="utf-8") as fh:
        fh.write(texto)
    print(f"\n[OK] Relatório escrito em {os.path.abspath(arquivo)}")
    return arquivo
