# 🎓 Curso Aplicado: Programação Robótica com ROS 2 no Rover Frugal 4WD/4WS
## Baseado na Obra: *"A Concise Introduction to Robot Programming with ROS2"* (Francisco Martín Rico, 2022)

---

## 🎯 Apresentação e Objetivo do Curso

Este curso foi estruturado para capacitar engenheiros, pesquisadores e estudantes na programação e controle autônomo de robôs móveis utilizando o **ROS 2 (Robot Operating System 2)**, tomando como objeto de estudo prático e experimental o **Rover Frugal 4WD/4WS de Transporte e Transposição de Escadas**.

Diferente de cursos genéricos com robôs diferenciais simples (ex: TurtleBot), este programa aborda os desafios reais de um veículo de **manobrabilidade omnidirecional ($\delta_M = 3$)**, suspensão complacente torsional (**C-STS**), rodas de **3 raios curvos** para transposição da **Escada de Blondel ($2E+P=64\text{ cm}$)** e carga útil pendular suspensa para transporte seguro de notebooks no campus **Itaipu Parquetec**.

```
                           [ARQUITETURA DO CURSO ROS 2]
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                  MÓDULO 10: Behavior Trees & Missão Autônoma                │
 ├──────────────────────────────────────┬──────────────────────────────────────┤
 │   MÓDULO 08: SLAM & Cartografia      │      MÓDULO 09: Navegação Nav2       │
 ├──────────────────────────────────────┴──────────────────────────────────────┤
 │        MÓDULO 07: Fusão Sensorial (EKF), LiDAR, IMU e Odometria             │
 ├──────────────────────────────────────┬──────────────────────────────────────┤
 │  MÓDULO 05: TF2 & Cinemática 4WS/4WD │ MÓDULO 06: URDF/Xacro & Gazebo Sim   │
 ├──────────────────────────────────────┴──────────────────────────────────────┤
 │     MÓDULO 02-04: Grafo Computacional (Tópicos, Serviços, Ações, Params)     │
 ├──────────────────────────────────────┬──────────────────────────────────────┤
 │  MÓDULO 01: Fundamentos & Workspace  │   MÓDULO 11: micro-ROS no ESP32      │
 └──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 📚 Estrutura dos Módulos

| Módulo | Título | Foco Temático (Martín Rico, 2022) | Aplicação no Rover Frugal |
| :---: | :--- | :--- | :--- |
| **[01](01_Fundamentos_ROS2_e_Workspace.md)** | **Fundamentos e Arquitetura** | Conceito DDS, nós, `rclpy`, `colcon` | Criação do workspace `rover_ws` e nó de telemetria |
| **[02](02_Topicos_Mensagens_e_Telemetria.md)** | **Grafo Computacional: Tópicos** | Publishers, Subscribers, QoS, custom msgs | Publicação de forças $F_z$, torque e deflexão C-STS |
| **[03](03_Servicos_e_Acoes_de_Missao.md)** | **Serviços e Ações Assíncronas** | Request/Response, Action Servers/Clients | Mudança de modo 4WS e Ação de Subir Escada de Blondel |
| **[04](04_Parametros_e_Configuracoes.md)** | **Parâmetros e Reconfiguração Dinâmica** | `rclpy.parameter`, arquivos YAML de runtime | Sintonia fina de rigidez $k_t$ e raio das rodas |
| **[05](05_Transformadas_TF2_e_Cinematica.md)** | **Transformadas de Coordenadas (TF2)** | `tf2_ros`, frames, quatérnios, cinemática | Árvore TF completa (`map` $\to$ `odom` $\to$ `base` $\to$ pernas) |
| **[06](06_URDF_Xacro_e_Gemeo_Digital_Gazebo.md)** | **Modelagem URDF/Xacro e Gazebo Sim** | Xacro paramétrico, SDF, `ros_gz_bridge` | Simulação das 4 rodas de raios e escadaria civil |
| **[07](07_Sensores_Odometria_e_Fusao_EKF.md)** | **Percepção e Fusão Sensorial** | Sensor msgs, IMU, LaserScan, EKF | Fusão EKF de odometria dos 4 motores com a IMU |
| **[08](08_Mapeamento_SLAM_e_Costmaps.md)** | **Mapeamento e Cartografia (SLAM)** | SLAM Toolbox, mapas 2D/3D de ocupação | Mapeamento da rota térreo $\to$ escada $\to$ sala da TI |
| **[09](09_Navegacao_Autonoma_Nav2.md)** | **Navegação Autônoma com Nav2** | Planners, Controllers (Pure Pursuit), Costmaps | Navegação omnidirecional 4WS desviando de pedestres |
| **[10](10_Behavior_Trees_e_Missao_Final.md)** | **Orquestração com Behavior Trees** | BehaviorTree.CPP / py_trees, árvores de missão | Missão completa autônoma de entrega de notebook |
| **[11](11_microROS_e_Hardware_ESP32.md)** | **Sistemas Embarcados com micro-ROS** | micro-ROS Agent, FreeRTOS, micro-ROS client | Ponte Wi-Fi/Serial entre ESP32 das rodas e ROS 2 |

---

## 🛠️ Pré-requisitos e Ambiente de Laboratório

* **Sistema Operacional**: Ubuntu 22.04 LTS (Nativo ou via WSL2 no Windows 11 com WSLg).
* **Distribuição ROS 2**: **ROS 2 Humble Hawksbill** (ou ROS 2 Jazzy Jalisco no Ubuntu 24.04).
* **Simulador**: **Gazebo Sim** (Harmonic / Fortress).
* **Linguagens**: Python 3.10+ (`rclpy`) e C++17 (`rclcpp`).

---

## 📖 Como Estudar Este Curso

1. Navegue sequencialmente pelos arquivos de cada módulo na pasta [`07_Curso_ROS2_Rover_Frugal/`](./).
2. Cada módulo contém:
   * **Exposição Teórica**: O conceito rigoroso do livro de Francisco Martín Rico.
   * **Implementação Prática**: Código Python (`rclpy`), Xacro ou YAML executável no Rover.
   * **Laboratório / Exercício**: Um desafio prático para você testar no simulador.
   * **Critérios de Homologação**: Como validar se o seu código atingiu os requisitos de engenharia.
