# Módulo 02: Grafo Computacional, Tópicos, Mensagens e Políticas de QoS
## Referência: Francisco Martín Rico (2022) — Capítulo 3

---

## 1. Fundamentação Teórica

### 1.1. Comunicação Baseada em Tópicos (Publish-Subscribe)
O padrão **Publish-Subscribe** desacopla temporalmente e espacialmente os nós produtores de informação dos nós consumidores:
* **Assíncrono e Não Bloqueante**: Publicadores transmitem dados sem esperar confirmação do receptor.
* **Múltiplos Produtores / Múltiplos Consumidores**: Vários nós podem publicar e assinar o mesmo tópico.

```
 [ESP32 / Rodas] ──> [/rover/wheel_telemetry] (100 Hz) ──> [Nó de Odometria]
                                                       └──> [Dashboard / GUI]
```

### 1.2. Políticas de Qualidade de Serviço (QoS)
Conforme detalhado por Francisco Martín Rico (2022), o ROS 2 permite configurar perfis de QoS específicos para cada fluxo de dados:

| Perfil de QoS | Confiabilidade (*Reliability*) | Durabilidade (*Durability*) | Caso de Uso no Rover |
| :--- | :---: | :---: | :--- |
| **Telemetria de Sensores (IMU, LiDAR)** | `BEST_EFFORT` | `VOLATILE` | Dados de alta frequência (100 Hz), onde o pacote mais recente é o único que importa. |
| **Comandos de Emergência (E-Stop)** | `RELIABLE` | `TRANSIENT_LOCAL` | Comandos críticos onde a perda de 1 único pacote é inaceitável. |
| **Parâmetros de Mapa / TF Estático** | `RELIABLE` | `TRANSIENT_LOCAL` | Novos nós recebem o último mapa publicado assim que inicializam. |

---

## 2. Definição de Mensagem Customizada

Para o Rover Frugal, precisamos publicar a telemetria detalhada de cada uma das 4 rodas de 3 raios curvos e a deflexão elástica do C-STS.

Crie o arquivo `msg/WheelTelemetry.msg`:
```text
std_msgs/Header header
string wheel_id                  # "FL", "FR", "RL", "RR"
float32 wheel_rpm                # Rotação atual (RPM)
float32 steer_angle_deg          # Ângulo de esterçamento atual (graus)
float32 normal_force_n           # Reação normal estimada Fz (N)
float32 csts_deflection_deg      # Deflexão angular da mola espiral C-STS (graus)
float32 elastic_energy_joules    # Energia potencial armazenada U = 0.5 * kt * Delta_theta^2 (J)
string kinematic_phase           # "CCS" (Contínuo) ou "DCS" (Transição de degrau)
```

---

## 3. Implementação Prática: Nó de Telemetria com QoS Otimizada

Vamos implementar em Python (`rover_telemetry_hub.py`) um nó de agregação que coleta dados em alta taxa com QoS `BEST_EFFORT` e emite estatísticas consolidadas:

```python
#!/usr/bin/env python3
"""
Módulo 02 - Agregador de Telemetria das 4 Rodas com Políticas de QoS
Autor: Baseado em Francisco Martín Rico (2022)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Twist

class RoverTelemetryHub(Node):
    def __init__(self):
        super().__init__('rover_telemetry_hub')

        # 1. Perfil de QoS para Sensores em Alta Taxa (IMU / Rodas)
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5
        )

        # 2. Perfil de QoS Confiável para Comandos Críticos
        command_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Assinantes
        self.sub_imu = self.create_subscription(
            Imu, '/imu/data', self.imu_callback, sensor_qos
        )
        self.sub_cmd = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_callback, command_qos
        )

        # Estados
        self.pitch_deg = 0.0
        self.roll_deg = 0.0
        self.is_stair_climbing = False

        self.get_logger().info("📊 [RoverTelemetryHub] Assinando tópicos com QoS configurada.")

    def imu_callback(self, msg: Imu):
        # Extrair aceleração e inclinação angular
        az = msg.linear_acceleration.z
        ax = msg.linear_acceleration.x
        
        # Estimar arfagem (Pitch) em graus
        import math
        self.pitch_deg = math.degrees(math.atan2(ax, az))

        # Detecção de degrau de Blondel: inclinação > 20 graus
        if abs(self.pitch_deg) > 20.0:
            if not self.is_stair_climbing:
                self.is_stair_climbing = True
                self.get_logger().warn(f"🪜 [ALERTA] Degrau detectado! Pitch = {self.pitch_deg:.1f}°")
        else:
            self.is_stair_climbing = False

    def cmd_callback(self, msg: Twist):
        self.get_logger().info(f"🎮 Comando: Linear = {msg.linear.x:.2f} m/s | Angular = {msg.angular.z:.2f} rad/s")

def main(args=None):
    rclpy.init(args=args)
    node = RoverTelemetryHub()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

---

## 🧪 Laboratório Prático 02

**Desafio**: 
1. Crie um nó publicador simulado (`mock_wheel_publisher.py`) que envie mensagens `WheelTelemetry` a **50 Hz** para as rodas `FL`, `FR`, `RL`, `RR`.
2. Configure o publicador para simular a transição **DCS** quando a roda girar $120^\circ$, elevando a deflexão do C-STS para $8^\circ$.
3. Use a ferramenta de linha de comando para medir a taxa real de transmissão:
   ```bash
   ros2 topic hz /rover/wheel_telemetry
   ros2 topic bw /rover/wheel_telemetry
   ```
