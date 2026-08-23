# 02. Auditoria Técnica do Projeto (R1 → R2)
## Achados, evidências e resoluções

> **Propósito.** Este documento registra, com evidência reproduzível, cada
> divergência ou erro encontrado na revisão R1 do projeto e o que foi feito a
> respeito. Ele existe para que ninguém precise redescobrir o mesmo problema
> — e para que a decisão de mudar (ou não mudar) o projeto seja rastreável.
>
> **Como ler.** Cada achado tem: o que estava escrito, por que está errado,
> o comando que reproduz a verificação, e a resolução adotada.
>
> **Severidade.** 🔴 impede a missão · 🟠 compromete requisito · 🟡 inconsistência
> documental · 🔵 melhoria de método.

---

## Sumário dos achados

| # | Achado | Severidade | Situação |
| :--- | :--- | :---: | :--- |
| [A-01](#a-01) | A roda Φ300 mm não transpõe o degrau de referência | 🔴 | Resolvido — Φ420 mm |
| [A-02](#a-02) | Roda de 3 raios é inutilizável em piso plano sem aro | 🔴 | Resolvido — aro elástico é item crítico |
| [A-03](#a-03) | Curso de suspensão de 35 mm satura na escada | 🔴 | Resolvido — 90 mm |
| [A-04](#a-04) | Rigidez do C-STS copiada de outra escala | 🔴 | Resolvido — redimensionada |
| [A-05](#a-05) | Classificação cinemática de Siegwart incorreta (δm+δs≠δM) | 🟠 | Resolvido — δm=1, δs=2 |
| [A-06](#a-06) | Holonomia declarada sem base; custo de troca de modo ignorado | 🟠 | Resolvido — documentado |
| [A-07](#a-07) | Torque calculado com raio de roda errado (0,10 m) | 🟠 | Resolvido — modelo completo |
| [A-08](#a-08) | Limite térmico dos motores nunca avaliado | 🟠 | Resolvido — I²t no firmware |
| [A-09](#a-09) | Limiar anti-tombamento dispara na subida normal | 🟠 | Resolvido — limiar por modo |
| [A-10](#a-10) | Atrito exigido na escada sem margem para piso molhado | 🟠 | Resolvido — restrição operacional |
| [A-11](#a-11) | Benchmark do C-STS produzido por fator de ajuste | 🔵 | Resolvido — física derivada |
| [A-12](#a-12) | Roda de raios era decorativa no protótipo 3D | 🔵 | Resolvido — contato real |
| [A-13](#a-13) | Contagem de raios divergente (3 x 4) | 🟡 | Resolvido — fonte única |
| [A-14](#a-14) | Massa divergente (7,5 kg x 10 kg) | 🟡 | Resolvido — fonte única |
| [A-15](#a-15) | Comprimentos de tubo do roteiro não fecham com a geometria | 🟡 | Resolvido — derivados do CAD |
| [A-16](#a-16) | Todos os links da documentação apontavam para `file:///d:/...` | 🟡 | Resolvido — links relativos |
| [A-17](#a-17) | Protótipo dependia de CDN externo | 🟡 | Resolvido — Three.js versionado |
| [A-18](#a-18) | `prototipo_3d_standalone.html` era cópia manual divergente | 🟡 | Resolvido — passou a ser build |
| [A-19](#a-19) | Economia "de até 75%" contra skid-steer sem base | 🟡 | Resolvido — modelo de Wong |
| [A-20](#a-20) | Ausência de rastreabilidade requisito → verificação | 🔵 | Resolvido — matriz de requisitos |

---

<a id="a-01"></a>
## A-01 🔴 A roda Φ300 mm não transpõe o degrau de referência

**O que estava escrito.** `02_Engenharia/05` deduzia o raio da roda assim:

> avanço linear por raio Δs = 2πr/3 ≥ P = 300 mm ⟹ r ≥ 143,26 mm,
> adotado r_max = 150 mm (Φ 300 mm).

**Por que está errado.** O critério usado é o de *rolamento em piso plano*: ele
compara o arco percorrido por raio com a **profundidade** do degrau. Mas uma roda
de raios não rola sobre a escada — ela **salta de nariz em nariz**. A distância a
vencer não é o piso *P*, é a diagonal nariz-a-nariz:

$$D = \sqrt{E^2 + P^2} = \sqrt{170^2 + 300^2} = 344{,}8\text{ mm}$$

E o alcance máximo de dois raios consecutivos, ambos tocando pela ponta, é a
corda do polígono regular inscrito:

$$\text{alcance} = 2\,r_{max}\,\sin(\pi/N)$$

**Condição de marcha síncrona (Eq. 1):**

$$\boxed{\;D \;\le\; 2\,r_{max}\sin(\pi/N)
\qquad\Longleftrightarrow\qquad
r_{max}\;\ge\;\frac{D}{2\sin(\pi/N)}\;}$$

Para *N* = 3 e o degrau de referência: **r_max ≥ 199,1 mm**.
A roda de R1 tem alcance de apenas **259,8 mm** contra **344,8 mm** exigidos —
déficit de 85 mm. Ela não alcança o nariz seguinte: cai no canto do degrau e
acaba apoiando na **face vertical do espelho**, onde a reação necessária sai do
cone de atrito e a roda escorrega em vez de subir.

**Evidência.**

```bash
python3 -c "
from simulador_python.geometria_escada import avaliar_robustez
print(avaliar_robustez(3, 0.150, 0.17, 0.30, raio_cubo=0.045).resumo())"
```

```
N=3 r_max=150 mm (Φ300 mm) em degrau 170x300 mm
  marcha síncrona ....... NÃO (margem -85.0 mm)
  robustez de fase ...... 0% das fases de aproximação escalam
```

![Comparação das duas rodas](../Imagens/simulacao/b1_dimensionamento_roda.png)

**Resolução.** O diâmetro foi redimensionado por **robustez de fase**: a fase com
que a roda chega ao primeiro degrau não é controlável pelo piloto, então o
projeto precisa escalar a partir de *qualquer* fase, e em *qualquer* escada da
família de Blondel (2E+P = 64 cm, E de 160 a 180 mm).

| Φ [mm] | E16/P32 | E17/P30 | E18/P28 | pior caso |
| ---: | ---: | ---: | ---: | ---: |
| 300 | 0% | 0% | 0% | **0%** |
| 400 | 75% | 83% | 92% | 75% |
| **420** | **100%** | **100%** | **100%** | **100%** ✔ |
| 440 | 100% | 100% | 100% | 75%¹ |
| 460 | 83% | 75% | 83% | 75% |

¹ falha em escadas fora de norma (E16/P28): a roda **sobredimensionada** ultrapassa
o nariz e cai dentro do degrau. O sucesso não é monotônico no raio — existe um
ótimo, e ele é **Φ420 mm**.

Consequências adotadas: entre-eixos travado em fase com a escada
(*L* = 2·D = 690 mm), vão livre do ventre de 190 mm e massa das rodas revista.

---

<a id="a-02"></a>
## A-02 🔴 A roda de 3 raios é inutilizável em piso plano sem aro elástico

**O que estava escrito.** O anel externo de banda de rodagem aparecia como
`CAD-07 — Tire-Tread-Ring (Opcional)`.

**Por que está errado.** Uma roda de *N* raios sem aro é uma *rimless wheel*. A
cota do cubo oscila entre `r_max` (raio apoiado na vertical) e `r_max·cos(π/N)`
(transferência entre raios). Para N = 3 e r_max = 210 mm:

$$\Delta y = r_{max}\left(1-\cos\frac{\pi}{N}\right) = 210\,(1-0{,}5) = \mathbf{105\ mm}$$

**105 mm de queda a cada 120° de rotação, em asfalto liso.** A missão é
majoritariamente piso plano — e o requisito de choque na carga é de 2,0 g.

**Evidência.**

```bash
python3 -m pytest testes/test_geometria_escada.py::test_ripple_em_piso_plano_e_o_da_roda_sem_aro -q
python3 -m pytest testes/test_suspensao.py::test_aro_elastico_e_indispensavel_em_piso_plano -q
```

Dinâmica com a carga a bordo, a 0,9 m/s em piso plano:

| Configuração | Pico na carga |
| :--- | ---: |
| com aro elástico | **0,58 g** ✔ |
| sem aro elástico | **7,69 g** ✘ |

**Resolução.** O aro passa a ser **item crítico, não opcional**, com bloco próprio
no arquivo mestre (`aro_elastico`). Ele fecha a superfície de rolamento no plano
e **colapsa localmente** na quina do degrau, liberando a ponta do raio para
engatar. A rigidez radial (3500 N/m) e a força de colapso local (90 N) são
parâmetros de projeto a **calibrar em bancada** — ver ensaio ENS-04 no protocolo
de testes.

> **Tensão de projeto a registrar.** Rolamento suave em piso plano e marcha
> síncrona em escada puxam para lados opostos: piso plano quer muitos raios
> (N ≥ 14 para ripple < 5 mm), escada quer poucos (N = 3 minimiza o raio). O aro
> elástico é o que permite atender aos dois com N = 3.

---

<a id="a-03"></a>
## A-03 🔴 Curso de suspensão de 35 mm satura na escada

**O que estava escrito.** `MAX_SUSP_TRAVEL = 0.035` (35 mm), sem justificativa.

**Por que está errado.** A marcha síncrona impõe quedas de cubo de até **89 mm**.
A energia a dissipar é

$$U = m\,g\,\Delta h = 8{,}72 \times 9{,}81 \times 0{,}089 = 7{,}6\ \text{J}$$

Com 35 mm de curso a suspensão bate no batente a cada transferência de raio e
transmite o choque direto à carga.

**Evidência.** Varredura curso × rigidez (escada, 0,25 m/s):

| Curso | Pico vertical na carga |
| ---: | ---: |
| 35 mm | 2,09 g ✘ (limite 2,0 g) |
| 60 mm | 1,37 g |
| **90 mm** | **0,81 g** ✔ |
| 110 mm | 0,81 g (sem ganho adicional) |

**Resolução.** Curso de **90 mm** com rigidez de **1000 N/m por roda**
(8 elásticos × 125 N/m), afundamento estático de 22 mm — 24% do curso, boa
prática veicular. Isso **muda o projeto mecânico do braço**: a manga de eixo
precisa de 90 mm de deslocamento vertical guiado, não 35 mm.

---

<a id="a-04"></a>
## A-04 🔴 A rigidez do C-STS foi copiada de outra escala

**O que estava escrito.** `KT_EMPIRICAL = 0.547` N·m/rad, valor medido por
Jeong & Kim (2025).

**Por que está errado.** Aquele valor foi medido no robô **do artigo**. Neste
rover o torque de acionamento de pico é de 5,40 N·m, o que daria

$$\Delta\theta = \frac{5{,}40}{0{,}547} = 9{,}87\ \text{rad} = 566^\circ$$

A mola enrolaria completamente e bateria no batente na primeira transferência de
raio. Transportar um resultado experimental entre escalas exige **semelhança
dimensional**, não cópia do número.

**Resolução.** A rigidez passa a ser **derivada do requisito**: torque de projeto
e deflexão admissível definem `kt = T/Δθ`; a geometria da espiral é resolvida da
rigidez, com verificação de tensão de flexão e de encaixe no cubo.

```
C-STS em PETG: b=30,0 mm, t=9,71 mm, L=386 mm, 1,5 voltas (r 20→62 mm)
  kt teórico / efetivo ..... 12,46 / 10,31 N·m/rad
  torque / deflexão projeto  5,40 N·m @ 30,0°
  tensão de flexão ......... 11,4 MPa (FS = 4,4)
```

O fator 0,828 medido por Jeong & Kim (razão entre rigidez experimental e teórica,
que reflete a aderência parcial entre filetes na impressão FDM) **continua sendo
usado** — é ele, e não o valor absoluto, o resultado transferível do artigo.

> **Efeito colateral relevante para a eletrônica.** Sob torque nominal a roda
> atrasa 30° em relação ao eixo do motor. Encoders montados no motor **não**
> medem a posição da roda: a odometria precisa de encoder no lado da roda ou de
> compensação explícita da complacência. Ver `02_Engenharia/08`.

---

<a id="a-05"></a>
## A-05 🟠 Classificação cinemática de Siegwart incorreta

**O que estava escrito.** Em `README`, `02_Engenharia/03` e `01_Planejamento/01`:

> δm = 2, δs = 4, δM = δm + δs ≥ 3

**Por que está errado.** 2 + 4 = 6, não 3. Além disso, Siegwart demonstra que
δs ≤ 2: com mais de duas rodas direcionais as demais são **redundantes** —
os ângulos não são livres, precisam convergir no mesmo ICR.

**Evidência.** O posto da matriz de restrições de deslizamento é calculado
numericamente:

```bash
python3 -c "
from simulador_python.kinematics import classificar_siegwart
print(classificar_siegwart(coordenado=True))
print(classificar_siegwart(coordenado=False))"
```

| Configuração das rodas | posto(C1s) | δm | δs | δM |
| :--- | ---: | ---: | ---: | ---: |
| coordenada (ICR comum) | 2 | **1** | **2** | **3** |
| descoordenada | 3 | 0 | 2 | — |

**Resolução.** O rover é da categoria **"Two-Steer"** da Tabela 3.1 de Siegwart:
δm = 1, δs = 2, δM = 3. O caso descoordenado não é curiosidade acadêmica: δm = 0
significa que **o veículo trava**. As quatro direções formam um sistema
sobre-restrito e qualquer erro de calibração vira arrasto lateral:

| Erro em UM servo | Arrasto lateral a 1 m/s |
| ---: | ---: |
| 0,5° | 7,8 mm/s |
| 1,0° | 15,5 mm/s |
| 2,0° | 31,1 mm/s |
| 5,0° | 77,6 mm/s |

Daí sai um requisito de montagem que não existia: **calibração dos servos 4WS
com erro ≤ 1,0°**, verificável em bancada.

---

<a id="a-06"></a>
## A-06 🟠 Holonomia declarada sem base, custo de troca de modo ignorado

**O que estava escrito.**

> O veículo é **holonômico no espaço de velocidades instantâneas**.

**Por que está errado.** Holonomia instantânea exige δm = 3 (rodas suecas ou
esféricas). Com rodas padrão direcionais δm = 1: o rover alcança qualquer
movimento no plano, mas **precisa parar e reorientar as rodas** antes de mudar a
direção instantânea.

**Resolução.** O custo de reconfiguração passa a ser um parâmetro do projeto e
entra no cronograma da missão:

| Transição | Tempo |
| :--- | ---: |
| ackermann → caranguejo | 0,56 s |
| ackermann → giro no eixo | 0,51 s |
| ackermann → escada | 0,10 s |

Além disso, o giro no próprio eixo exige β = ±49° (= atan(L/W)), acima dos ±45°
originalmente especificados. O curso de esterçamento foi elevado para **±55°**.

---

<a id="a-07"></a>
## A-07 🟠 Torque de tração calculado com o raio errado

**O que estava escrito.** `02_Engenharia/04` calculava
`T_total = F_total · r` com **r = 0,10 m**, enquanto o resto do projeto usava
0,15 m. O resultado (1,63 N·m por motor) subestima em 50% já pelo raio, e ignora
completamente o torque geométrico de içamento sobre o nariz do degrau.

**Resolução.** Substituído por modelo completo em `simulador_python/powertrain.py`:
curva torque-velocidade real do motor CC, redutor com rendimento, e o **torque de
içamento medido na marcha** (braço horizontal do contato × carga normal).

| Grandeza | R1 | R2 |
| :--- | ---: | ---: |
| Raio adotado | 0,10 m (inconsistente) | 0,210 m |
| Massa | 10 kg (inconsistente) | 8,72 kg |
| Torque de pico exigido | não avaliado | **5,40 N·m** |
| Redução | 1:50 a 1:70 | **1:172** |
| Torque de stall na saída | 3,5 N·m (catálogo) | **12,49 N·m** |
| Margem na escada | não avaliada | **1,67** ✔ (KPI ≥ 1,50) |

A hipótese de carga também foi corrigida: **na subida a transferência é para
trás**, portanto quem faz o esforço de içamento são as rodas **traseiras**
(25,4 N cada), não as dianteiras.

---

<a id="a-08"></a>
## A-08 🟠 O limite térmico dos motores nunca foi avaliado

**Por que importa.** No regime de escada o motor opera a **~11% de rendimento**:
quase toda a potência elétrica vira calor no enrolamento.

| Corrente por motor | Regime térmico | Tempo até 115 °C |
| ---: | ---: | ---: |
| 3,02 A | 115 °C | ∞ (contínua admissível) |
| 5,0 A | 255 °C | 108 s |
| 6,9 A | 457 °C | 50 s |
| 9,2 A | 781 °C | **27 s** |

Um lance de 8 degraus a 0,25 m/s leva ~11 s. **Dois lances consecutivos sem pausa
consomem quase toda a margem térmica.**

**Resolução.** O limite de missão em escada é **térmico, não energético** (a
bateria gasta apenas 15% da energia útil na missão inteira). Requisito novo para
o firmware: **proteção I²t com pausa de resfriamento obrigatória entre lances**
(`02_Engenharia/08`).

---

<a id="a-09"></a>
## A-09 🟠 O limiar anti-tombamento dispara na subida normal

**O que estava escrito.**

> Se o ângulo de arfagem ultrapassar o limiar crítico de 40°, o firmware
> desacelera os motores automaticamente.

**Por que está errado.** A escada de referência tem 29,5° de inclinação, e a
oscilação da marcha de 3 raios soma mais ±14°: a arfagem em **operação normal**
chega a **43°**. O limiar de 40° abortaria toda subida no meio.

**Resolução.** Limiar **dependente de modo**, com o tombamento estático (52,6°)
como referência:

| Modo | Limiar de arfagem |
| :--- | ---: |
| piso / rampa | 35° |
| escada | 52° |

---

<a id="a-10"></a>
## A-10 🟠 Atrito exigido na escada não tem margem para piso molhado

**Evidência.** O coeficiente mínimo para subir a 29,5° com resistência de
rolamento de degrau é **μ ≥ 0,72**.

| Superfície | μ disponível | Sobe? |
| :--- | ---: | :---: |
| Concreto seco | 0,85 | ✔ (margem 1,18) |
| Concreto molhado | 0,55 | ✘ |
| Mármore polido | 0,40 | ✘ |

**Resolução.** Restrição operacional explícita: **proibida a subida de escadas com
piso molhado ou polido**, com bloqueio do modo escada no firmware até confirmação
do piloto. Entra no protocolo de missão e na matriz de riscos.

---

<a id="a-11"></a>
## A-11 🔵 O benchmark do C-STS era produzido por fator de ajuste

**O que estava escrito** (`spoke_contact_physics.py`, R1):

```python
if self.phase_name == 'DCS':
    # Desaceleração amortecida em > 50%
    self.deceleration_spike = abs((self.prev_linear_v - cur_v) / dt) * 0.35
else:
    self.deceleration_spike = abs((self.prev_linear_v - cur_v) / dt)
```

**Por que é um problema.** A "redução de 65% do choque com C-STS" não era uma
previsão do modelo: era o próprio fator `0.35` sendo reimpresso na saída. O
gráfico comparativo provava apenas que `0.35 < 1.00`.

**Resolução.** A cadeia causal foi fechada de ponta a ponta, sem nenhum fator
livre:

```
geometria da roda + perfil do degrau
   → SimuladorMarcha devolve a trajetória REAL do cubo (eventos de contato)
   → a queda de cubo medida vira a excitação de base do modelo dinâmico
   → aro, elásticos e C-STS filtram a excitação com suas rigidezes de projeto
   → o pêndulo da caixa filtra o que chega ao notebook
   → a aceleração da carga é INTEGRADA
```

Ligar ou desligar um estágio muda apenas a rigidez correspondente; o ganho
aparece — ou não — por conta própria. O resultado, agora derivado:

| Caminho | Pico na carga |
| :--- | ---: |
| ponta rígida, sem suspensão | 20,2 g |
| só C-STS (estágio 1) | 1,4 g |
| C-STS + elásticos (estágios 1+2) | **1,2 g** |

---

<a id="a-12"></a>
## A-12 🔵 A roda de raios curvos era decorativa no protótipo 3D

**O que estava escrito** (`app.js`, R1):

```javascript
const terrainY = getTerrainHeight(wx, wz);
const targetY = terrainY + 0.15;                      // raio FIXO
roverState.wheelHeights[i] = THREE.MathUtils.damp(roverState.wheelHeights[i], targetY, 10, dt);
```

**Por que é um problema.** A roda era tratada como **disco de raio constante**.
Toda a mecânica que o projeto defende — raios curvos, transferência CCS/DCS,
C-STS, aro elástico — era animação sem efeito. O simulador não conseguiria
mostrar a falha de A-01 nem o ganho de A-02.

**Resolução.** `prototipo_3d/fisica.js` implementa a mesma cadeia do modelo
Python: assentamento real dos raios contra o terreno roda a roda, aro elástico
como piso de contato, quatro massas não suspensas, corpo com arfagem e rolagem,
C-STS integrada, motor com curva real, bateria e térmica. O protótipo agora
**reproduz** o achado A-01 quando se troca para a roda Φ300 pelo botão de
comparação.

---

<a id="a-13"></a>
## A-13 🟡 Contagem de raios divergente

`README`, `02_Engenharia/02`, `02_Engenharia/05` e o simulador diziam **3 raios**;
`03_Simulacao/01` (catálogo CAD, peça `CAD-03`) dizia **4 raios curvos de perfil
espiral logarítmica**. O perfil também divergia: "espiral logarítmica" em um
documento, "arco circular" em outro.

**Resolução.** `roda.num_raios_N = 3` no arquivo mestre, perfil definido por
`varredura_rad` e `expoente_perfil` — a mesma parametrização usada pelo simulador
Python e pelo modelo 3D. N = 3 é justificado em A-01: minimiza o raio exigido.

---

<a id="a-14"></a>
## A-14 🟡 Massa divergente

`simulador_python/config.py` usava 7,5 kg; `02_Engenharia/04` dimensionava a
tração com 10 kg; `01_Planejamento/04` falava em carga útil de 3,0 kg sem
declarar a massa seca.

**Resolução.** Massa passou a ser **soma de subconjuntos declarados**, verificada
por teste (`test_massa_total_e_soma_das_partes`): 6,22 kg secos + 2,50 kg de carga
= **8,72 kg**.

---

<a id="a-15"></a>
## A-15 🟡 Comprimentos de tubo do roteiro não fecham com a geometria

`05_Execucao/01` mandava cortar hastes de 350 mm e 400 mm. Com as posições de
junta do modelo 3D de R1, os tubos necessários eram de 430 mm e 420 mm — e com a
geometria de R2 mudam de novo.

**Resolução.** Os comprimentos de corte deixam de ser digitados no roteiro e
passam a ser **derivados da geometria** (ver `05_Execucao/01`, tabela de corte
gerada a partir do arquivo mestre).

---

<a id="a-16"></a>
## A-16 🟡 Links apontando para o disco local do autor

Todos os links de todos os documentos usavam
`file:///d:/Downloads/Rascunho%20Rover/...`. No GitHub, no computador de qualquer
outra pessoa e na apresentação ao Parquetec, **nenhum deles funciona**.

**Resolução.** Todos convertidos para caminhos relativos.

---

<a id="a-17"></a>
## A-17 🟡 O protótipo dependia de CDN externo

O `index.html` importava Three.js de `unpkg.com`. Sem internet — ou atrás de
proxy corporativo, que é exatamente o caso de um parque tecnológico — o
protótipo abre em tela preta.

**Resolução.** Three.js r160 versionado em `prototipo_3d/vendor/three/`
(licença MIT incluída). O protótipo funciona **offline**.

---

<a id="a-18"></a>
## A-18 🟡 O standalone era uma cópia manual divergente

Existiam duas implementações do protótipo: `prototipo_3d/` (modular) e
`prototipo_3d_standalone.html` (cópia). Elas já haviam divergido em R1.

**Resolução.** O standalone passou a ser **artefato de build**
(`ferramentas/gerar_standalone.py`), com aviso no cabeçalho. Fonte é só uma.

---

<a id="a-19"></a>
## A-19 🟡 Comparação com skid-steer sem base

R1 afirmava economia "de até 75%" e implementava:

```python
p_skid = p_roll_4ws + (lateral_friction_force * linear_speed * 1.8)   # 1.8 = ?
```

**Resolução.** Substituído pelo momento resistente de derrapagem de Wong
(cap. 6), `M_r = μ_t·W·L/4`, com a potência de manobra `M_r·ω`. A 0,8 m/s em
curva de 1,2 m: 2,1 W (4WS) contra 10,5 W (skid-steer) — **80% de economia**,
agora com fórmula rastreável.

---

<a id="a-20"></a>
## A-20 🔵 Não havia rastreabilidade requisito → verificação

R1 tinha KPIs numa tabela e ensaios em outra, sem vínculo. Não era possível
responder "qual ensaio prova o requisito de choque na carga?".

**Resolução.** [`01_Requisitos_e_Rastreabilidade.md`](01_Requisitos_e_Rastreabilidade.md)
com identificadores REQ-###, método de verificação (análise, simulação, ensaio ou
demonstração), artefato de evidência e situação atual de cada requisito.

---

## Como reproduzir toda a auditoria

```bash
pip install -r requirements.txt

python3 -m simulador_python.main --parametros   # configuração resolvida
python3 -m simulador_python.main --marcha       # marcha na escada de referência
python3 -m simulador_python.main --sintese      # varredura do espaço de projeto
python3 -m simulador_python.main --relatorio    # relatório completo + figuras
python3 -m pytest testes/ -q                    # 73 verificações automatizadas
```
