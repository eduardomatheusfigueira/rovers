# Pacote ROS 2 + Gazebo Sim para o Rover Frugal 4WD/4WS

Este pacote fornece a integração completa do **Rover Frugal 4WD/4WS** com o **ROS 2 (Humble / Jazzy)** e o **Gazebo Sim (Harmonic / Fortress)** através do `ros_gz_bridge` e nós em `rclpy`.

---

## 🏗️ Arquitetura da Integração

```mermaid
graph TD
    Nav2[Nav2 / SLAM Toolbox / Teleop] -->|/cmd_vel| Ctrl[controller_4ws.py (rclpy)]
    
    subgraph ROS 2 Layer
        Ctrl -->|Juntas 4WS/4WD| Bridge[ros_gz_bridge]
        Sensors[LiDAR /scan + IMU /imu/data] <---|Tópicos Sensores| Bridge
        RSP[robot_state_publisher] -->|/robot_description| RViz[RViz2]
        Ctrl -->|/odom + /tf| Nav2
    end
    
    subgraph Gazebo Sim Layer
        Bridge <-->|gz.msgs / Protobuf| GzSim[Gazebo Sim Server (gz-sim)]
        GzSim --> World[Mundo: Escada de Blondel (blondel_stairs.sdf)]
        GzSim --> Rover[Modelo URDF: Pernas em V + 3 Raios Curvos]
    end
```

---

## 📦 Estrutura do Pacote

* **`urdf/rover_frugal.urdf.xacro`**: Modelo cinemático e inercial completo com o chassi em X, caixa organizadora pendular, 4 juntas de direção ($\beta_1..\beta_4$) e 4 rodas de 3 raios curvos ($\Phi 420\text{ mm}$ e $\Phi 300\text{ mm}$).
* **`worlds/blondel_stairs.sdf`**: Cenário de simulação com a escada normativa de Blondel ($E = 17\text{ cm}$, $P = 30\text{ cm}$, $2E+P=64\text{ cm}$).
* **`config/ros_gz_bridge.yaml`**: Mapeamento bidirecional transparente de tópicos ROS 2 $\leftrightarrow$ Gazebo.
* **`rover_gazebo_ros2/controller_4ws.py`**: Nó em `rclpy` que traduz comandos de velocidade `/cmd_vel` para os ângulos de esterçamento e rotação dos 4 motores de tração ($\delta_M = 3$), publicando `/odom` e `/tf`.
* **`launch/gazebo_sim.launch.py`**: Arquivo de inicialização único que sobe o Gazebo, faz o spawn do robô, inicia a ponte e o nó controlador.

---

## 🚀 Como Compilar e Executar no ROS 2 (Ubuntu 22.04 / 24.04 ou WSL2)

### 1. Pré-requisitos
Certifique-se de ter o ROS 2 (Humble ou Jazzy) e os pacotes do Gazebo instalados:
```bash
sudo apt update
sudo apt install -y \
  ros-$ROS_DISTRO-ros-gz \
  ros-$ROS_DISTRO-ros-gz-bridge \
  ros-$ROS_DISTRO-ros-gz-sim \
  ros-$ROS_DISTRO-robot-state-publisher \
  ros-$ROS_DISTRO-joint-state-publisher \
  ros-$ROS_DISTRO-xacro \
  ros-$ROS_DISTRO-teleop-twist-keyboard
```

### 2. Compilar o Workspace
Copie ou crie um link simbólico da pasta `rover_gazebo_ros2` dentro de `~/ros2_ws/src/`:
```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
ln -s "/caminho/para/Rascunho Rover/rover_gazebo_ros2" .
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### 3. Executar a Simulação no Gazebo
```bash
ros2 launch rover_gazebo_ros2 gazebo_sim.launch.py
```

### 4. Pilotar o Rover (Teleop Keyboard)
Em outro terminal:
```bash
source ~/ros2_ws/install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

---

## 🧭 Integração com Nav2 e SLAM

O modelo já publica:
* **LiDAR 2D (`/scan`)**: Para mapeamento com `slam_toolbox` ou `cartographer`.
* **IMU (`/imu/data`)**: Para fusão sensorial com `robot_localization` (EKF).
* **Odometria (`/odom`)**: Calculada pelo nó cinemático `controller_4ws`.

### Para iniciar o SLAM:
```bash
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=True
```

### Para iniciar a Navegação Autônoma (Nav2):
```bash
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=True
```
