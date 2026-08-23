# Módulo 07: Percepção, Odometria e Fusão Sensorial com EKF
## Referência: Francisco Martín Rico (2022) — Capítulo 9

---

## 1. Fundamentação Teórica

### 1.1. O Problema do Desvio Odométrico em Rodas de Raios e Escadas
Ao subir escadas ou solos irregulares, as rodas sofrem escorregamentos pontuais e transições de raio (**DCS**), gerando erros acumulativos na odometria por contagem de pulsos de encoders (*Wheel Odometry Drift*).

### 1.2. Filtro de Kalman Estendido (EKF / `robot_localization`)
O pacote padrão **`robot_localization`** executa a fusão probabilística de múltiplas fontes sensoriais assíncronas:
* **Odometria das 4 Rodas (100 Hz)**: Alta resolução em velocidade linear ($v_x, v_y$) e deslocamento.
* **Unidade Inercial IMU 9-DOF (100 Hz)**: Taxas angulares precisas de giroscópio ($\omega_z$) e acelerações lineares ($a_x, a_y, a_z$).

```
 [Encoders 4WD] ──> [/rover/wheel_odom] ──┐
                                          ├──> [ekf_node (robot_localization)] ──> [/odometry/filtered]
 [IMU 9-DOF]    ──> [/imu/data]        ──┘                                         └──> TF [odom -> base_footprint]
```

---

## 2. Configuração do EKF em YAML (`ekf_config.yaml`)

```yaml
ekf_filter_node:
  ros__parameters:
    frequency: 50.0
    two_d_mode: false # True 3D mode (essencial para estimar arfagem e subida de escadas)
    publish_tf: true
    map_frame: map
    odom_frame: odom
    base_link_frame: base_footprint
    world_frame: odom

    # Configuração da Odometria de Rodas
    odom0: /odom
    odom0_config: [true,  true,  true,   # X, Y, Z
                   false, false, false,  # Roll, Pitch, Yaw
                   true,  true,  true,   # vx, vy, vz
                   false, false, false,  # vroll, vpitch, vyaw
                   false, false, false]  # ax, ay, az
    odom0_differential: false

    # Configuração da IMU
    imu0: /imu/data
    imu0_config: [false, false, false,  # X, Y, Z
                  true,  true,  true,   # Roll, Pitch, Yaw (Orientação)
                  false, false, false,  # vx, vy, vz
                  true,  true,  true,   # vroll, vpitch, vyaw (Velocidades angulares)
                  true,  true,  true]   # ax, ay, az (Acelerações lineares)
    imu0_differential: false
    imu0_remove_gravitational_acceleration: true
```

---

## 3. Invocação do EKF no Launch File

```python
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=['config/ekf_config.yaml', {'use_sim_time': True}]
        )
    ])
```

---

## 🧪 Laboratório Prático 07

**Desafio**: 
1. Suba uma escada de Blondel de 3 degraus apenas com a odometria de rodas e plote a trajetória no RViz2.
2. Ative o `ekf_node` fundindo com a IMU e compare a redução do desvio (*drift*) na estimativa de altitude ($Z$) e arfagem (*Pitch*).
