# 02. Roadmap Futuro — Fase B: Uso Dual, Aplicações Táticas e Controle por Fibra Óptica
## Imunidade Eletromagnética Total (*Zero-EW Vulnerability*) e Transmissão Óptica Não-Radiante

---

## 1. Justificativa Estratégica do Uso Dual e Desafio da Guerra Eletrônica

Nos cenários modernos de segurança de infraestruturas críticas, defesa civil, resgate tático e ambientes hostis de combate, os veículos terrestres operados por rádiofrequência (RF) enfrentam severas limitações:
1. **Guerra Eletrônica Ativa (*Jamming*)**: Transmissores de ruído eletromagnético de alta potência bloqueiam instantaneamente enlaces de rádio (Wi-Fi, 915 MHz, 2.4 GHz, 5.8 GHz e GPS).
2. **Localização de Emissões (*Radio Direction Finding*)**: A emissão de RF do rover ou da estação do piloto pode ser triangulada por sensores inimigos, expondo a posição do operador.
3. **Atenuação em Ambientes Confinados**: Sinais de rádio não atravessam múltiplos subsolos de concreto armado, túneis de cabos de hidrelétricas, galerias subterrâneas ou escombros de desastres.

```mermaid
graph TD
    A[Vulnerabilidades de RF em Ambientes Hostis] --> B[Bloqueio por Jamming / Guerra Eletrônica]
    A --> C[Triangulação e Detecção do Piloto]
    A --> D[Perda de Sinal em Túneis e Bunkers]
    
    subgraph Solução Tática: Controle por Fibra Óptica (Fase B)
        E[Carretel de Microfibra Óptica Embarcado] --> F[100% Imune a Jamming e Ruído Eletromagnético]
        E --> G[Emissão Zero de RF - Totalmente Silencioso]
        E --> H[Vídeo 4K / HD Não-Comprimido sem Latência]
        E --> I[Penetração Total em Subsolos e Ambientes Blindados]
    end
```

---

## 2. Arquitetura do Sistema de Controle por Fibra Óptica

A **Fase B** implementa o conceito de **UGV Cabeado por Microfibra Descartável (*Tethered Optical Rover*)**:

```
 [Estação do Piloto / Bunker]
        |
    [Media Converter Óptico BiDi]
        |
        |~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ (1 km a 5 km de Microfibra)
        | (O cabo fica parado no solo; é desenrolado pelo próprio rover)
        |
    [Carretel Dispensador Central Embarcado no Rover]
        |
    [Transceiver Óptico SFP 1310/1550nm Monomodo]
        |
    [ESP32 / Controlador Interno + Câmeras HD]
```

### 2.1. Princípio do Carretel Dispensador Interno (*Inside-Out Spool*)
* O carretel de microfibra óptica não fica na base, mas **embarcado na traseira/fundo do próprio rover**.
* À medida que o UGV se desloca, a microfibra é liberada suavemente por desenrolamento interno axial (*stationary payout*), repousando estática sobre o solo.
* **Vantagem Mecânica**: O cabo não é arrastado pelo terreno, eliminando o atrito contra pedras, quinas ou vegetação, o que evita o rompimento da fibra mesmo em curvas complexas.

### 2.2. Especificação do Meio Óptico e Eletrônica
* **Fibra Óptica Monomodo Insensível à Curvatura (Padrão ITU-T G.657.B3)**: Permite raios de curvatura de até $5 \text{ mm}$ sem atenuação de sinal significativa.
* **Diâmetro do Microcabo**: Cabo ultrafino com revestimento de aramida/polímero de alta tração ($\varnothing \approx 0,8 \text{ a } 1,2 \text{ mm}$), pesando menos de $1,5 \text{ kg por quilômetro}$.
* **Transceptor Bidirecional (BiDi SFP 1.25 Gbps ou 10 Gbps)**: Utiliza **uma única via de fibra** para transmissão e recepção simultâneas por divisão de comprimento de onda (WDM: 1310 nm Tx / 1550 nm Rx).
* **Capacidade de Dados**: Transmissão simultânea de 4 câmeras Full HD/4K, telemetria completa dos 4 motores e canais de comando com **latência de fibra de apenas 5 microssegundos por quilômetro**.

---

## 3. Aplicações Táticas e de Uso Dual (Defesa e Infraestrutura Crítica)

| Missão Operacional | Cenário de Emprego | Vantagem do Rover Frugal com Fibra |
| :--- | :--- | :--- |
| **Inspeção em Galerias de Itaipu** | Túneis de drenagem, condutos forçados e poços da usina hidrelétrica com altíssima blindagem eletromagnética. | Navegação contínua em profundidade sem perda de imagem e sem necessitar de repetidores de rádio. |
| **Desativação de Explosivos (EOD / Bomb Disposal)** | Verificação e aproximação de pacotes suspeitos sem risco de detonar detonadores acionados por rádio. | Operação com emissão de RF estritamente zero, eliminando acionamento acidental de artefatos. |
| **Reconhecimento Tático em Ambiente com *Jamming*** | Infiltração em instalações industriais tomadas ou zonas de desastre com bloqueadores de sinal ativos. | Imunidade inabalável a qualquer sistema de guerra eletrônica (*anti-jamming absoluto*). |
| **Varredura QBRN (Química, Biológica, Radiológica, Nuclear)** | Entrada em ambientes contaminados transportando sensores na caixa organizadora modular. | Estrutura de PVC de baixo custo permite o descarte ou descontaminação ácida rápida do chassi após a missão. |

---

## 4. Integração Modular no Chassi Frugal

A transição da plataforma base (Fase 6) para a versão tática com fibra óptica (Fase 7.2) é viabilizada pela modularidade nativa do chassi:
1. O carretel óptico é instalado dentro da caixa organizadora ou em um berço de PVC na traseira dos braços.
2. A placa controladora ESP32 recebe a placa conversora SPI/Ethernet-to-Fiber.
3. As rodas de raios curvos e a geometria pendular continuam operando normalmente para vencer escombros e escadas em ambientes urbanos colapsados.
