# 02. Rodas em Raios Curvos (*Curved Spokes*) e Suspensão Complacente Torsional (C-STS)
## Fundamentação Matemática Rigorosa baseada em Jeong & Kim (2025), Terramecânica (Wong, 2022) e Mecanismos (Sclater, 2001)

---

## 1. Definição Geométrica Exata da Roda com 3 Raios Curvos (Jeong & Kim, 2025)

Conforme a caracterização matemática de **Jeong & Kim (2025)** (*Experimental Investigation of a Passive Compliant Torsional Suspension for Curved-Spoke Wheel Stair Climbing, Appl. Sci. 2025, 15, 5985*), a roda é composta por **três raios curvos ($N = 3$)** defasados angularmente em $120^\circ$ ($\Delta\theta = 2\pi/3$):

```
       [Geometria da Roda de 3 Raios Curvos - Jeong & Kim, 2025]
                     .---.
                   /       \
                  |  (C-STS) |----- Eixo Motriz (Motorredutor 12V 4WD)
                 / \       / \
                /   '--.--'   \
               /       |       \
        Raio 1        Raio 2    Raio 3  <-- Arcos de Curvatura com Raio r0
              \        |        /
               '--.    |    .--'
                   \   |   /
             _______'--+--'________
            |  Degrau de Escada ($S \times H = 300\text{ mm} \times 160\text{ mm}$)
```

### 1.1. Equações Cinemáticas de Contato e Fases do Movimento
Durante a escalada de um degrau com largura de piso $S$ e espelho $H$, o raio de curvatura instantâneo $r(t)$ (distância entre o Centro de Rotação - CoR e o ponto de contato com o solo) evolui em duas fases distintas:

1. **Estado de Contato Contínuo (*Continuous Contact State - CCS*)**:
   * O raio de contato cresce monotonicamente de $r_{min}$ (cubo da roda) até $r_{max}$ (ponta do raio):
     $$r(t) \in [r_{min}, r_{max}]$$
   * Sob velocidade angular constante $\omega$, a velocidade linear do CoR cresce continuamente até atingir o pico máximo imediatamente antes da transição:
     $$v_{max, i} = \omega \cdot r_{max}$$

2. **Estado de Contato Descontínuo (*Discontinuous Contact State - DCS*)**:
   * No instante em que o contato salta para o degrau superior, o raio efetivo despenca bruscamente de $r_{max}$ para $r_{min}$.
   * A velocidade linear cai instantaneamente para o valor mínimo:
     $$v_{min, i+1} = \omega \cdot r_{min}$$
   * **Queda de Velocidade Teórica ($\Delta v_i$)**:
     $$\Delta v_i = v_{max, i} - v_{min, i+1} = \omega \cdot (r_{max} - r_{min})$$

---

## 2. A Métrica de Instabilidade Dinâmica e a Solução C-STS

### 2.1. Desaceleração de Impacto na Carga Útil
Devido à inércia do rover e da carga (notebook), a velocidade linear não pode cair instantaneamente a zero. Ocorre uma desaceleração finita e violenta no intervalo $\Delta t_i$ do DCS:

$$a_i = \frac{\Delta v_i}{\Delta t_i} = \frac{v_{max, i-1} - v_{min, i}}{\Delta t_i}$$

Essa desaceleração brusca ($a_i$) gera momentos de tombamento, derrapagem (*wheel slip*) e vibrações prejudiciais à eletrônica.

```mermaid
graph TD
    A[Giro da Roda de 3 Raios Curvos] --> B[Fase CCS: r cresce de r_min a r_max]
    B --> C[Transição DCS: Salto Instantâneo de r_max para r_min]
    C --> D[Queda Brusca Δv_i = ω(r_max - r_min)]
    D --> E[Pico Severo de Desaceleração a_i e Torque de Stall]
    
    subgraph Sistema de Supressão Híbrido: C-STS + Elásticos
        E -.->|Absorvido pelo Cubo| CSTS["<b>Módulo C-STS no Cubo (Jeong & Kim, 2025)</b><br>• Mola Espiral Plana em PLA/PETG<br>• Rigidez Torsional kt = E·b·t³ / (12·L)<br>• Armazena energia em CCS e ejeta em DCS"]
        E -.->|Absorvido pelo Braço| ELAST["<b>Suspensão por Elásticos (Sclater & Chironis)</b><br>• Amortecimento Histerético Natural<br>• Filtragem de Ondulações Verticais"]
        CSTS & ELAST --> F[Redução > 40% na Desaceleração + Ganho de Velocidade Média]
    end
```

---

## 3. Dimensionamento do Mecanismo C-STS (Mola Espiral Plana)

Conforme a formulação de vigas espirais de *Jeong & Kim (2025, Seção 3.3)*, a rigidez torsional teórica da mola espiral plana ($k_t$) é dada por:

$$k_t = \frac{E \cdot b \cdot t^3}{12 \cdot L}$$

Onde:
* $E$: Módulo de elasticidade do material ($E_{PLA} \approx 3,5 \times 10^9 \text{ N/m}^2$, $E_{PETG} \approx 2,1 \times 10^9 \text{ N/m}^2$).
* $b$: Largura axial da espiral ($b = 15\text{ mm}$).
* $t$: Espessura da lâmina espiral ($t = 4\text{ a } 6\text{ mm}$).
* $L$: Comprimento desenrolado da espiral ($L \approx 827,28\text{ mm}$).

| Variante do C-STS | Espessura ($t$) | Rigidez Teórica ($k_t$) | Rigidez Experimental Medida | Comportamento em Teste de Escada |
| :--- | :---: | :---: | :---: | :--- |
| **Baixa Rigidez (*Soft*)** | $4,0\text{ mm}$ | $0,246\text{ N}\cdot\text{m/rad}$ | $0,206\text{ N}\cdot\text{m/rad}$ | Máxima absorção de choque, maior deflexão angular. |
| **Média Rigidez (*Baseline*)** | $5,0\text{ mm}$ | $0,661\text{ N}\cdot\text{m/rad}$ | $0,547\text{ N}\cdot\text{m/rad}$ | **Configuração Ótima**: equilíbrio entre torque e velocidade. |
| **Alta Rigidez (*Stiff*)** | $6,0\text{ mm}$ | $1,157\text{ N}\cdot\text{m/rad}$ | $0,909\text{ N}\cdot\text{m/rad}$ | Menor deflexão, resposta rígida em alta velocidade. |

---

## 4. Sinergia de Dois Estágios: C-STS no Cubo + Elásticos na Manga

Para aliar a precisão da pesquisa de Jeong & Kim (2025) à filosofia de custo mínimo do projeto frugal, a suspensão opera em **dois estágios complementares**:

```
 [Eixo do Motorredutor 4WD]
             |
     [Módulo C-STS Torsional]  <-- 1º Estágio: Absorve a descontinuidade DCS da roda
             |
     [Roda com 3 Raios Curvos]
             |
    [Manga 4WS com Elásticos] <-- 2º Estágio: Absorve choques verticais do relevo (PVC/Chassi)
```

1. **Estágio 1 (Torsional no Cubo - C-STS)**: Permite que a roda gire brevemente em sentido reverso em relação ao eixo do motor no momento do choque, armazenando energia elástica e a liberando para "catapultar" a ponta do raio sobre o degrau seguinte.
2. **Estágio 2 (Linear na Haste - Elásticos de Escritório)**: Permite o deslocamento vertical suave ($\Delta z$) de toda a manga de eixo, isolando a caixa organizadora pendular de vibrações de alta frequência.

---

## 5. Especificações de Fabricação em Impressão 3D

* **Geometria dos Raios**: 3 raios em espiral com espessura de $8\text{ mm}$ na raiz, afinando para $6\text{ mm}$ na extremidade externa, com raio máximo $r_{max} = 120\text{ mm}$ (diâmetro total $240\text{ mm}$).
* **Ponta de Contato (*Tread Grip*)**: Pastilha de borracha vulcanizada de alta fricção ($\mu > 0,85$) fixada na extremidade de cada raio curvo para garantir engate antiderrapante em quinas de concreto e mármore.
* **Preenchimento de Impressão 3D**: $100\%$ de preenchimento (*solid infill*) nos raios e no anel interno do C-STS para evitar falhas por fadiga de cisalhamento.
