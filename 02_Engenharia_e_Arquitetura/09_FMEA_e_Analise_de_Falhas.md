# 09. FMEA — Análise de Modos de Falha e Efeitos
## Da matriz qualitativa de riscos para uma análise com RPN e ações verificáveis

> R1 tinha uma matriz probabilidade × impacto com seis riscos posicionados por
> julgamento. Aqui os modos de falha são levantados **por subsistema**, com
> severidade, ocorrência, detecção e ação — no formato clássico de FMEA de
> produto. Vários modos só ficaram visíveis depois da análise física de R2.

**Escalas (1 a 10).**
**S** severidade do efeito · **O** probabilidade de ocorrência ·
**D** dificuldade de detecção antes do efeito · **RPN = S × O × D**.

**Critério de ação:** RPN ≥ 100 exige ação de projeto antes da Fase 4;
RPN ≥ 200 é bloqueante.

---

## 1. Subsistema: roda e contato com o solo

| # | Modo de falha | Efeito | S | O | D | RPN | Ação |
| :--- | :--- | :--- | :-: | :-: | :-: | --: | :--- |
| F-01 | Aro elástico rígido demais: não colapsa na quina | roda não engata, não sobe | 9 | 5 | 3 | **135** | ENS-04 mede a força de colapso antes da montagem final; aro segmentado com molas de lâmina como plano B |
| F-02 | Aro elástico macio demais: colapsa em piso plano | ripple de 105 mm, choque na carga | 8 | 4 | 2 | 64 | mesma calibração ENS-04; telemetria de `carga_vert_g` detecta em operação |
| F-03 | Fratura de raio curvo no impacto contra a quina | perda de tração, missão abortada | 8 | 4 | 3 | 96 | impressão deitada (camadas acompanham a curvatura), 5 perímetros, 100% de preenchimento na raiz; banco de rodas reserva |
| F-04 | Desgaste da pastilha de borracha da ponta | atrito cai abaixo de 0,72, escorrega | 7 | 5 | 4 | **140** | pastilha substituível por parafuso; inspeção antes de cada missão; verificação de μ no ENS-06 |
| F-05 | Roda escorrega na face do espelho | não sobe, pode descer de volta | 9 | 3 | 3 | 81 | resolvido por projeto (marcha síncrona, [A-01](../00_Especificacao_Mestre/02_Auditoria_Tecnica.md#a-01)); detecção por discrepância odometria × IMU |
| F-06 | Piso molhado ou polido | atrito insuficiente, escorregamento | 9 | 5 | 2 | 90 | bloqueio do modo escada com confirmação do piloto ([A-10](../00_Especificacao_Mestre/02_Auditoria_Tecnica.md#a-10)) |

---

## 2. Subsistema: suspensão

| # | Modo de falha | Efeito | S | O | D | RPN | Ação |
| :--- | :--- | :--- | :-: | :-: | :-: | --: | :--- |
| F-10 | Ruptura de elástico do feixe | rigidez cai, curso satura | 5 | 7 | 2 | 70 | feixe redundante (8 unidades: perder 1 muda 12,5%); troca em < 30 s; substituição preventiva a cada 10 ciclos |
| F-11 | Deformação plástica acumulada do feixe | afundamento estático cresce, ventre encosta no nariz | 7 | 6 | 5 | **210** ⛔ | ENS-11 mede a deformação residual; **calço de ajuste** no projeto do braço para recuperar a altura; considerar mola helicoidal comercial se residual > 15% |
| F-12 | Espiral C-STS bate no batente a cada transferência | choque transmitido, fadiga da lâmina | 6 | 4 | 4 | 96 | dimensionada para 30° com batente em 35°; deflexão vai na telemetria |
| F-13 | Fadiga da lâmina C-STS em PETG | perda de rigidez progressiva | 7 | 4 | 6 | **168** | FS 4,4 em tensão estática, mas **vida em fadiga do PETG impresso é desconhecida**: ENS-12 com 5000 ciclos antes da Fase 5 |
| F-14 | Batente de fim de curso quebra | sobre-extensão destrói os elásticos | 6 | 3 | 3 | 54 | batente metálico (parafuso + porca) em vez de impresso |

---

## 3. Subsistema: tração e energia

| # | Modo de falha | Efeito | S | O | D | RPN | Ação |
| :--- | :--- | :--- | :-: | :-: | :-: | --: | :--- |
| F-20 | Sobretemperatura do enrolamento em lances consecutivos | queima do motor | 9 | 6 | 5 | **270** ⛔ | proteção I²t obrigatória ([A-08](../00_Especificacao_Mestre/02_Auditoria_Tecnica.md#a-08)); pausa de resfriamento imposta; NTC de calibração no ENS-13 |
| F-21 | Célula não sustenta 4,6C de pico | queda de tensão, reset do MCU | 8 | 4 | 3 | 96 | REQ-303 verifica o datasheet antes da compra; capacitor de tampão no barramento |
| F-22 | Driver BTS7960 em proteção térmica sob carga | perda de tração de uma roda | 7 | 4 | 3 | 84 | dissipador + ventilação forçada; margem de 200% na corrente nominal |
| F-23 | Redutor planetário com folga (*backlash*) | odometria e controle degradados | 5 | 6 | 5 | 150 | redutor metálico (não plástico); folga medida no ENS-02 e compensada |
| F-24 | Acoplador da roda solta sob torque de içamento | roda gira solta, perda de tração | 8 | 4 | 4 | 128 | acoplador sextavado com dois prisioneiros a 90° e trava química; verificação no checklist pré-missão |

---

## 4. Subsistema: esterçamento 4WS

| # | Modo de falha | Efeito | S | O | D | RPN | Ação |
| :--- | :--- | :--- | :-: | :-: | :-: | --: | :--- |
| F-30 | Erro de calibração de um servo | arrasto lateral, corrente extra, desvio de rota | 5 | 7 | 6 | **210** ⛔ | rotina de calibração no ENS-02 com erro ≤ 1,0° ([A-05](../00_Especificacao_Mestre/02_Auditoria_Tecnica.md#a-05)); referência mecânica (pino) na manga |
| F-31 | Servo sem resposta (engrenagem quebrada) | sistema sobre-restrito trava (δm = 0) | 9 | 3 | 2 | 54 | servo com realimentação de posição; supervisor detecta e trava o modo |
| F-32 | Saturação de esterçamento não sinalizada | odometria erra silenciosamente | 4 | 6 | 7 | 168 | flag de saturação no OSD e na telemetria ([A-05](../00_Especificacao_Mestre/02_Auditoria_Tecnica.md#a-05)) |
| F-33 | Rolamento 608ZZ da manga travado por poeira | esterçamento duro, servo satura | 5 | 5 | 4 | 100 | vedação labiríntica na manga; lubrificação no checklist |

---

## 5. Subsistema: estrutura e carga

| # | Modo de falha | Efeito | S | O | D | RPN | Ação |
| :--- | :--- | :--- | :-: | :-: | :-: | --: | :--- |
| F-40 | Junta split-clamp escorrega no tubo de PVC | geometria muda, roda desalinha | 7 | 5 | 5 | **175** | torque de aperto especificado (1,8 a 2,2 N·m); marca de referência pintada no tubo denuncia deslizamento visualmente |
| F-41 | Trinca no PVC por sobreaperto do clamp | perda estrutural do braço | 8 | 4 | 6 | 192 | torquímetro obrigatório na montagem; inspeção visual das orelhas |
| F-42 | Presilha toggle abre sob vibração | caixa se solta dos braços | 10 | 2 | 3 | 60 | presilha com trava secundária (contrapino); verificação no checklist pré-missão |
| F-43 | Notebook desliza dentro da caixa | choque lateral no equipamento | 6 | 6 | 3 | 108 | berço de espuma recortado + cinta de velcro; ENS-08 valida com acelerômetro na carga |
| F-44 | Ventre encosta no nariz do degrau | trava no meio do lance | 8 | 3 | 2 | 48 | vão livre de 190 mm por projeto, com dois critérios ([06](06_Sintese_da_Roda_e_Geometria_de_Escalada.md) §4.2) |

---

## 6. Subsistema: controle e teleoperação

| # | Modo de falha | Efeito | S | O | D | RPN | Ação |
| :--- | :--- | :--- | :-: | :-: | :-: | --: | :--- |
| F-50 | Perda de enlace dentro do prédio | rover parado em local inacessível | 7 | 6 | 2 | 84 | failsafe em 300 ms + retorno assistido; ELRS 915 MHz; teste de cobertura no ENS-10 |
| F-51 | Failsafe deixa as rodas livres em rampa | rover desce sozinho | 9 | 3 | 3 | 81 | freio dinâmico por curto nas pontes H |
| F-52 | Limiar anti-tombamento aborta subida normal | missão não completa | 6 | 8 | 2 | 96 | limiar dependente de modo ([A-09](../00_Especificacao_Mestre/02_Auditoria_Tecnica.md#a-09)) |
| F-53 | Latência de vídeo alta engana o piloto | manobra errada, colisão | 6 | 4 | 4 | 96 | VTX analógico ≤ 50 ms; medição no ENS-10 |
| F-54 | Odometria errada por complacência do C-STS | posição estimada diverge | 4 | 8 | 6 | 192 | encoder no lado da roda ou compensação explícita ([A-04](../00_Especificacao_Mestre/02_Auditoria_Tecnica.md#a-04)) |

---

## 7. Consolidado: o que precisa ser resolvido antes da Fase 4

| RPN | Modo | Bloqueio |
| ---: | :--- | :--- |
| **270** | F-20 sobretemperatura do motor | ⛔ proteção I²t implementada e testada |
| **210** | F-11 deformação plástica dos elásticos | ⛔ ENS-11 concluído com critério de aceite |
| **210** | F-30 calibração dos servos 4WS | ⛔ rotina de calibração validada (ENS-02) |
| **192** | F-41 trinca no PVC por sobreaperto | torquímetro na bancada |
| **192** | F-54 odometria x complacência do C-STS | decisão sobre posição do encoder |
| **175** | F-40 escorregamento do split-clamp | procedimento com marca de referência |
| **168** | F-13 fadiga do C-STS em PETG | ENS-12 com 5000 ciclos |
| **168** | F-32 saturação silenciosa | flag na telemetria |
| **150** | F-23 folga do redutor | medição e compensação |
| **140** | F-04 desgaste da pastilha | pastilha substituível |
| **135** | F-01 janela de colapso do aro | ENS-04 |

```mermaid
quadrantChart
    title Modos de falha — ocorrência x severidade (tamanho = dificuldade de detecção)
    x-axis "Baixa severidade" --> "Alta severidade"
    y-axis "Baixa ocorrência" --> "Alta ocorrência"
    quadrant-1 "Monitorar de perto"
    quadrant-2 "Prioridade crítica"
    quadrant-3 "Aceitar"
    quadrant-4 "Prevenir por projeto"
    "F-20 térmica do motor": [0.90, 0.60]
    "F-11 fadiga dos elásticos": [0.70, 0.60]
    "F-30 calibração 4WS": [0.50, 0.70]
    "F-54 odometria C-STS": [0.40, 0.80]
    "F-13 fadiga do C-STS": [0.70, 0.40]
    "F-01 aro não colapsa": [0.90, 0.50]
    "F-40 clamp escorrega": [0.70, 0.50]
    "F-42 presilha abre": [1.00, 0.20]
    "F-50 perda de enlace": [0.70, 0.60]
```

---

## 8. O que mudou em relação à matriz de riscos de R1

| Risco de R1 | Situação em R2 |
| :--- | :--- |
| R1 fadiga dos elásticos | mantido e agravado (F-11, RPN 210): o curso de 90 mm exige mais dos elásticos |
| R2 fratura de raios curvos | mantido (F-03), com ação de orientação de impressão |
| R3 superaquecimento dos drivers | **reclassificado**: o gargalo térmico é o **motor** (F-20), não o driver |
| R4 latência de rádio | mantido (F-50, F-53) |
| R5 desalinhamento dos braços de PVC | desdobrado em F-40 e F-41, com procedimento de aperto |
| R6 atraso na entrega de peças | risco de cronograma, migrado para `01_Planejamento/03` |
| — | **novo:** F-01/F-02, janela de operação do aro elástico |
| — | **novo:** F-20, limite térmico dos motores |
| — | **novo:** F-30/F-54, consequências do sistema sobre-restrito e da complacência |
| — | **novo:** F-06, atrito insuficiente em piso molhado |
