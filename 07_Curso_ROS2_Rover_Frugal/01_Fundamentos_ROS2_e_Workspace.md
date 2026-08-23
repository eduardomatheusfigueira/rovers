# Módulo 01: Fundamentos do ROS 2, Arquitetura DDS e Workspace
## Referência: Francisco Martín Rico (2022) — Capítulos 1 e 2

---

## 1. Fundamentação Teórica

### 1.1. O que é o ROS 2 e a Camada DDS
O **ROS 2** (*Robot Operating System 2*) não é um sistema operacional tradicional, mas um *middleware* robótico distribuído de alta confiabilidade. Diferente do ROS 1 (que dependia de um nó mestre centralizado `roscore`), o ROS 2 baseia-se no padrão industrial **DDS (Data Distribution Service)**:

```
 ┌────────────────────────────────────────────────────────┐
 │            Aplicação do Rover (rclpy / rclcpp)         │
 ├────────────────────────────────────────────────────────┤
 │              RCL (ROS Client Library C API)            │
 ├────────────────────────────────────────────────────────┤
 │         RMW (ROS Middleware Interface: rmw_cyclonedds) │
 ├────────────────────────────────────────────────────────┤
 │      DDS (Data Distribution Service / RTPS UDP/IP)     │
 └────────────────────────────────────────────────────────┘
```

* **Descoberta Dinâmica Descentralizada**: Nós encontram-se automaticamente na rede local sem servidor central.
* **Segurança e Tempo Real**: Suporte nativo a comunicação determinística e criptografia (SROS 2).
* **Qualidade de Serviço (QoS)**: Controle fino de latência, confiabilidade (*Reliable* vs *Best Effort*) e durabilidade de mensagens.

---

## 2. Estrutura de Workspace no Projeto do Rover

No ROS 2, todo desenvolvimento ocorre dentro de um **Workspace `colcon`**:

```bash
mkdir -p ~/rover_ws/src
cd ~/rover_ws/src
```

### Criando o Pacote Central do Rover com `ament_python`:
```bash
ros2 pkg create --build-type ament_python rover_core --dependencies rclpy std_msgs sensor_msgs geometry_msgs
```

---

## 3. Implementação Prática: Nó de Heartbeat e Telemetria

Vamos criar o primeiro nó em Python (`rover_heartbeat_node.py`), responsável por monitorar o estado geral do Rover (tensão da bateria Li-Ion 4S, modo operacional e temperatura estimada dos motores):

```python
#!/usr/bin/env python3
"""
Módulo 01 - Nó de Monitoramento e Heartbeat do Rover Frugal
Autor: Baseado em Francisco Martín Rico (2022)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32

class RoverHeartbeatNode(Node):
    def __init__(self):
        super().__init__('rover_heartbeat_node')
        
        # Parâmetros de monitoramento
        self.battery_voltage = 16.4  # Bateria 4S totalmente carregada (V)
        self.motor_temperature = 32.0 # Temperatura dos motores (°C)
        
        # Publicadores
        self.pub_status = self.create_publisher(String, '/rover/system_status', 10)
        self.pub_battery = self.create_publisher(Float32, '/rover/battery_voltage', 10)
        
        # Timer de execução a 2 Hz (a cada 0.5s)
        self.timer = self.create_timer(0.5, self.timer_callback)
        
        self.get_logger().info("✅ [RoverHeartbeatNode] Inicializado com sucesso!")

    def timer_callback(self):
        # Simulação de descarga suave da bateria
        self.battery_voltage = max(13.2, self.battery_voltage - 0.001)
        
        # Publicar Tensão
        v_msg = Float32()
        v_msg.data = self.battery_voltage
        self.pub_battery.publish(v_msg)
        
        # Publicar Status do Sistema
        s_msg = String()
        s_msg.data = f"MODO: 4WS_ACKERMANN | BATERIA: {self.battery_voltage:.2f}V | TEMP: {self.motor_temperature:.1f}C"
        self.pub_status.publish(s_msg)

def main(args=None):
    rclpy.init(args=args)
    node = RoverHeartbeatNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("🛑 Encerrando RoverHeartbeatNode...")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

---

## 4. Compilação e Execução

No terminal:
```bash
cd ~/rover_ws
colcon build --symlink-install
source install/setup.bash

# Executar o nó:
ros2 run rover_core rover_heartbeat_node
```

### Inspecionando o Grafo Computacional:
Em outro terminal:
```bash
# Listar nós ativos:
ros2 node list

# Ler os tópicos publicados em tempo real:
ros2 topic echo /rover/system_status
ros2 topic echo /rover/battery_voltage
```

---

## 🧪 Laboratório Prático 01

**Desafio**: Adicione ao nó `RoverHeartbeatNode` uma verificação de alarme:
Se a tensão da bateria cair abaixo de **$13,8\text{ V}$** (limite de segurança da célula 4S), o nó deve emitir um alerta em vermelho no log com `self.get_logger().warn(...)` e publicar no tópico `/rover/alarm` uma mensagem de retorno imediato à base.
