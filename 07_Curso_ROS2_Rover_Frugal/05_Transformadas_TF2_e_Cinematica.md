# Módulo 05: Árvore de Transformadas (TF2) e Cinemática Omnidirecional 4WS
## Referência: Francisco Martín Rico (2022) — Capítulo 7

---

## 1. Fundamentação Teórica

### 1.1. O Sistema de Coordenadas e a Norma REP-105
Na robótica móvel, as relações espaciais entre o mapa, a odometria e cada peça do robô são mantidas por uma árvore de transformadas dinâmica chamada **TF2**:

```
 [map] ──(SLAM)──> [odom] ──(Odometria)──> [base_footprint]
                                                 │
                                                 ▼
                                            [base_link]
                      ┌──────────────────────────┼──────────────────────────┐
                      ▼                          ▼                          ▼
             [payload_box_link]          [fl_knuckle_link]          [fr_knuckle_link]
              ┌───────┴───────┐                  │                          │
              ▼               ▼                  ▼                          ▼
         [lidar_link]    [imu_link]       [fl_wheel_link]            [fr_wheel_link]
```

* **`map`**: Referencial global estático inercial (corrigido pelo SLAM).
* **`odom`**: Referencial local contínuo e suave baseado na contagem de pulsos dos encoders das rodas e IMU.
* **`base_footprint`**: Projeção 2D do robô no plano do solo ($Z = 0$).
* **`base_link`**: Centro geométrico do chassi em X.

---

## 2. Cinemática Omnidirecional 4WS/4WD ($\delta_M = 3$, Siegwart & Nourbakhsh)

Diferente de um robô diferencial convencional ($\delta_M = 2$), o Rover Frugal possui **4 rodas com esterçamento independente ($\beta_1..\beta_4$) e tração independente ($\omega_1..\omega_4$)**:

$$\begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\psi} \end{bmatrix} = \mathbf{J}(\beta) \begin{bmatrix} \omega_1 \\ \omega_2 \\ \omega_3 \\ \omega_4 \end{bmatrix}$$

### Modos Operacionais Fundamentais:
1. **Ackermann Duplo Contrassimétrico**: Rodas dianteiras e traseiras esterçam em sentidos opostos ($\beta_r = -\beta_f$), reduzindo o raio de curva pela metade sem arrasto de pneus.
2. **Modo Caranguejo (*Crab Steering*)**: Todas as 4 rodas viram no mesmo ângulo ($\beta_1 = \beta_2 = \beta_3 = \beta_4 = \theta$), permitindo ao robô transladar diagonalmente mantendo a câmera apontada para a frente.
3. **Giro em Torno do Eixo (*Spin Turn*)**: Rodas alinham-se tangentes à circunferência circunscrita ($R = \sqrt{L^2+W^2}/2$), realizando giro de raio zero no próprio lugar.
4. **Modo Escada (*Stair Climbing*)**: Eixos alinhados paralelamente ($\beta = 0$) com sincronismo de rotação a $120^\circ$.

---

## 3. Implementação Prática: Publicador Dinâmico de TF2 em Python

Vamos implementar o nó `rover_tf_broadcaster.py`, responsável por publicar as transformadas de todas as juntas dinâmicas:

```python
#!/usr/bin/env python3
"""
Módulo 05 - Publicador Dinâmico da Árvore TF2 do Rover Frugal
Autor: Baseado em Francisco Martín Rico (2022)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from sensor_msgs.msg import JointState
import tf2_ros
import numpy as np

class RoverTFBroadcaster(Node):
    def __init__(self):
        super().__init__('rover_tf_broadcaster')
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Assinar o estado das juntas das pernas e rodas
        self.sub_joints = self.create_subscription(
            JointState, '/joint_states', self.joint_callback, 10
        )
        self.get_logger().info("🌐 [RoverTFBroadcaster] Publicador de TF2 ativo.")

    def joint_callback(self, msg: JointState):
        now = self.get_clock().now().to_msg()

        # Dicionário de posições de juntas
        joint_dict = dict(zip(msg.name, msg.position))

        # Publicar TF do Pêndulo da Caixa de Carga
        pendulum_pitch = joint_dict.get('payload_pendulum_joint', 0.0)
        t_box = TransformStamped()
        t_box.header.stamp = now
        t_box.header.frame_id = 'base_link'
        t_box.child_frame_id = 'payload_box_link'
        t_box.transform.translation.x = 0.0
        t_box.transform.translation.y = 0.0
        t_box.transform.translation.z = -0.04

        # Quatérnio a partir do Pitch pendular
        q_box = self.euler_to_quaternion(0.0, pendulum_pitch, 0.0)
        t_box.transform.rotation.x = q_box[0]
        t_box.transform.rotation.y = q_box[1]
        t_box.transform.rotation.z = q_box[2]
        t_box.transform.rotation.w = q_box[3]
        self.tf_broadcaster.sendTransform(t_box)

    def euler_to_quaternion(self, roll, pitch, yaw):
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)
        return [
            sr * cp * cy - cr * sp * sy, # x
            cr * sp * cy + sr * cp * sy, # y
            cr * cp * sy - sr * sp * cy, # z
            cr * cp * cy + sr * sp * sy  # w
        ]

def main(args=None):
    rclpy.init(args=args)
    node = RoverTFBroadcaster()
    rclpy.spin(node)
    rclpy.shutdown()
```

---

## 4. Visualização e Depuração de TF no RViz2

```bash
# Abrir o visualizador RViz2:
ros2 run rviz2 rviz2

# Gerar o diagrama da árvore de TF atual em PDF:
ros2 run tf2_tools view_frames

# Inspecionar a transformada instantânea entre o laser e a base:
ros2 run tf2_ros tf2_echo base_link lidar_link
```

---

## 🧪 Laboratório Prático 05

**Desafio**: Implemente a transformada estática entre a caixa organizadora (`payload_box_link`) e o sensor LiDAR (`lidar_link`) usando um `StaticTransformBroadcaster`. O sensor deve ficar posicionado a $+18\text{ cm}$ à frente ($X = +0.18$) e $+12\text{ cm}$ acima da tampa ($Z = +0.12$).
