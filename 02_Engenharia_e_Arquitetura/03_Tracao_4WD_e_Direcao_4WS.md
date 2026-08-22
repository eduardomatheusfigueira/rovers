# 03. Cinemática de Locomoção: Tração 4WD e Esterçamento 4WS
## Modelo Cinemático Rigoroso (Siegwart & Nourbakhsh, 2004), ICR e Eficiência Energética (Wong, 2022)

---

## 1. Topologia Mecatrônica e Grau de Manobrabilidade

O rover frugal é projetado com **8 atuadores independentes** (4 motores de tração DC com redução e encoders + 4 servomotores digitais de esterçamento com retorno de posição):

```mermaid
graph TD
    subgraph Arquitetura 4WD + 4WS
        MCU[Controlador Central ESP32 - FreeRTOS] --> D1[Driver Tração Dianteiro Esq. 4WD]
        MCU --> D2[Driver Tração Dianteiro Dir. 4WD]
        MCU --> D3[Driver Tração Traseiro Esq. 4WD]
        MCU --> D4[Driver Tração Traseiro Dir. 4WD]
        MCU --> S1[Servo Esterçamento Dianteiro Esq. 4WS]
        MCU --> S2[Servo Esterçamento Dianteiro Dir. 4WS]
        MCU --> S3[Servo Esterçamento Traseiro Esq. 4WS]
        MCU --> S4[Servo Esterçamento Traseiro Dir. 4WS]
    end
```

### Grau de Manobrabilidade $\delta_M = 3$ (Siegwart & Nourbakhsh, 2004)
Conforme a formulação clássica de *Siegwart & Nourbakhsh (Intro to Autonomous Mobile Robots, Cap. 3)*:
* **Grau de Mobilidade**: $\delta_m = 2$ (velocidade longitudinal e lateral instantânea no plano).
* **Grau de Dirigibilidade**: $\delta_s = 4$ (orientação independente dos 4 planos de roda).
* **Grau de Manobrabilidade**: $\delta_M = \delta_m + \delta_s \ge 3$.

> **Implicação Fundamental**: O veículo é **holonômico no espaço de velocidades instantâneas**, sendo capaz de transladar em qualquer ângulo no plano ($X, Y$) e rotacionar ($\dot{\theta}$) de forma totalmente desacoplada, sem necessitar de rodas Mecanum/suecas frágeis e ineficientes.

---

## 2. Modelagem Cinemática e Restrições de Rolamento Puro

Seja o vetor de postura do robô no referencial global $\xi_I = [x, y, \theta]^T$ e a velocidade no referencial do robô $\dot{\xi}_R = [\dot{x}_R, \dot{y}_R, \dot{\theta}_R]^T = R(\theta) \dot{\xi}_I$.

Para cada uma das 4 rodas orientáveis ($i = 1, 2, 3, 4$), posicionadas nas coordenadas polares $(l_i, \alpha_i)$ com ângulo de esterçamento $\beta_i$ e raio $r$:

```
                       ESQUEMA CINEMÁTICO DA RODA ORIENTÁVEL (i)
                                     y_R ^
                                         |    / V_i (Vetor de Velocidade da Roda)
                                         |   /
                            (x_i, y_i) --+--/---> beta_i (Ângulo de Esterçamento)
                                         | /  |
                                         |/   |
                                         +----+---------> x_R
                                        /
                                       / l_i (Distância Radial)
                                      /
                                     O (Centro de Massa / Origem do Robô)
```

### 2.1. Condição de Rolamento Longitudinal sem Escorregamento
$$[\cos(\alpha_i + \beta_i) \quad \sin(\alpha_i + \beta_i) \quad l_i \sin\beta_i] \dot{\xi}_R = r \dot{\varphi}_i$$

Onde $\dot{\varphi}_i$ é a velocidade angular de rotação do motor de tração da roda $i$.

### 2.2. Condição de Não-Deslizamento Lateral (Restrição Não-Holonômica Instantânea)
$$[-\sin(\alpha_i + \beta_i) \quad \cos(\alpha_i + \beta_i) \quad l_i \cos\beta_i] \dot{\xi}_R = 0$$

Ao orientar dinamicamente os 4 ângulos $\beta_i$ através dos servos 4WS, o controlador ESP32 garante que todas as retas normais às rodas convirjam exatamente para um único **Centro Instantâneo de Rotação (ICR)**, eliminando o escorregamento lateral (*lateral scrub*).

---

## 3. Modos Operacionais de Navegação e Cálculo do ICR

```mermaid
graph LR
    subgraph Modos Cinemáticos 4WS
        M1["<b>Modo 1: Ackermann Duplo</b><br>Curvas fechadas em corredores"]
        M2["<b>Modo 2: Movimento Caranguejo</b><br>Translação lateral pura (β1=β2=β3=β4)"]
        M3["<b>Modo 3: Giro no Eixo (Spin Turn)</b><br>Rotação de 360° em raio zero"]
        M4["<b>Modo 4: Modo Escada</b><br>Eixos travados e tração 4WD sincronizada"]
    end
```

### 3.1. Modo 1: Ackermann Duplo (Geometria 4WS - Wong, 2022)
Para uma curva com raio $R$ no centro da caixa e entre-eixos $L$:
$$\delta_{frente} = \arctan\left(\frac{L/2}{R \mp B/2}\right), \quad \delta_{traseira} = -\arctan\left(\frac{L/2}{R \mp B/2}\right)$$
* As rodas dianteiras e traseiras giram em sentidos opostos, reduzindo o raio de curva pela metade em relação a veículos comuns e permitindo transitar em portas de $80\text{ cm}$.

### 3.2. Modo 2: Movimento em Caranguejo (*Crab Walk*)
* Todos os 4 servos assumem o mesmo ângulo $\beta_1 = \beta_2 = \beta_3 = \beta_4 = \theta_{desejado}$.
* Todos os 4 motores giram na mesma velocidade linear $v$.
* O rover translada lateralmente ou diagonalmente sem alterar a orientação do chassi.

### 3.3. Modo 3: Rotação no Próprio Eixo (*Zero-Radius Spin Turn*)
* O ICR é posicionado exatamente no Centro de Gravidade ($x_{ICR} = 0, y_{ICR} = 0$).
* Os 4 servos posicionam as rodas perpendiculares às diagonais do "X": $\beta_i = \alpha_i \pm 90^\circ$.
* As rodas do lado esquerdo e direito giram em sentidos contrários, efetuando rotação de $360^\circ$ sobre a própria projeção da caixa.

---

## 4. Comparativo de Eficiência Energética: 4WS vs Skid-Steering (Wong, 2022)

Conforme a análise de terramecânica de *J. Y. Wong (Theory of Ground Vehicles, Cap. 6)*, veículos com direção por derrapagem diferencial (*Skid-Steer*) demandam um momento resistente lateral gigantesco devido ao atrito por arraste dos pneus:

$$M_{resiste\_skid} = \frac{\mu_{lateral} \cdot W \cdot L}{4}$$

| Métrica de Desempenho | Skid-Steering Convencional | Arquitetura 4WS com Servos (Adotada) |
| :--- | :--- | :--- |
| **Atrito Lateral nas Curvas** | Alto (Deslizamento forçado contínuo) | **Nulo (Rolamento puro com alinhamento de ICR)** |
| **Pico de Corrente em Manobra** | $12\text{A a } 20\text{A}$ (motores em quase-stall) | **$< 3,5\text{A}$ (corrente de rolamento suave)** |
| **Desgaste das Rodas 3D** | Rápida abrasão dos raios de plástico | **Mínimo desgaste (preserva os raios curvos)** |
| **Autonomia de Bateria** | Reduzida em até 40% em pisos rugosos | **Autonomia maximizada ($\ge 45\text{ minutos}$)** |
