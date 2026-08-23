# Módulo 06: Modelagem URDF/Xacro e Gêmeo Digital no Gazebo Sim
## Referência: Francisco Martín Rico (2022) — Capítulo 8

---

## 1. Fundamentação Teórica

### 1.1. URDF (Unified Robot Description Format) e Xacro
O **URDF** é a linguagem XML padronizada no ROS para descrever a cinemática e a dinâmica de robôs:
* **`link`**: Corpos rígidos com propriedades visuais (malhas CAD/primitivas), de colisão e **matrizes de inércia $3\times3$** ($I_{xx}, I_{yy}, I_{zz}, I_{xy}, I_{xz}, I_{yz}$).
* **`joint`**: Conexões articuladas entre links pai e filho (`revolute`, `continuous`, `prismatic`, `fixed`).
* **`xacro`**: Extensão com macros, propriedades matemáticas e laços de repetição, eliminando código duplicado.

---

## 2. Anatomia Xacro das 4 Pernas em V Invertido

No arquivo [`rover_gazebo_ros2/urdf/rover_frugal.urdf.xacro`](../rover_gazebo_ros2/urdf/rover_frugal.urdf.xacro), criamos a macro paramétrica para instanciar as 4 pernas radiais:

```xml
<xacro:macro name="rover_leg" params="prefix pos_x pos_y">
  <!-- Manga de Esterçamento (Knuckle 4WS) -->
  <link name="${prefix}_knuckle_link">
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="0.25"/>
      <inertia ixx="0.005" ixy="0" ixz="0" iyy="0.005" iyz="0" izz="0.005"/>
    </inertial>
    <visual>
      <geometry><cylinder radius="0.035" length="0.10"/></geometry>
      <material name="clamp_orange"/>
    </visual>
    <collision>
      <geometry><cylinder radius="0.035" length="0.10"/></geometry>
    </collision>
  </link>

  <!-- Junta de Direção: Giro em Z (+-45 graus) -->
  <joint name="${prefix}_steer_joint" type="revolute">
    <parent link="base_link"/>
    <child link="${prefix}_knuckle_link"/>
    <origin xyz="${pos_x} ${pos_y} -0.15" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="-0.785" upper="0.785" effort="15.0" velocity="3.0"/>
  </joint>

  <!-- Roda de 3 Raios Curvos (Propulsão Contínua) -->
  <link name="${prefix}_wheel_link">
    <inertial>
      <origin xyz="0 0 0" rpy="${pi/2} 0 0"/>
      <mass value="0.75"/>
      <inertia ixx="0.012" ixy="0" ixz="0" iyy="0.012" iyz="0" izz="0.020"/>
    </inertial>
    <visual>
      <origin xyz="0 0 0" rpy="${pi/2} 0 0"/>
      <geometry><cylinder radius="0.065" length="0.080"/></geometry>
      <material name="clamp_orange"/>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="${pi/2} 0 0"/>
      <geometry><cylinder radius="0.210" length="0.080"/></geometry>
    </collision>
  </link>

  <!-- Junta de Tração Contínua -->
  <joint name="${prefix}_wheel_joint" type="continuous">
    <parent link="${prefix}_knuckle_link"/>
    <child link="${prefix}_wheel_link"/>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <axis xyz="0 1 0"/>
  </joint>
</xacro:macro>
```

---

## 3. Ponte Bidirecional `ros_gz_bridge`

Para conectar os motores e sensores simulados no **Gazebo Sim** aos tópicos do **ROS 2**, usamos o arquivo de configuração YAML:

```yaml
- ros_topic_name: "/cmd_vel"
  gz_topic_name: "/cmd_vel"
  ros_type_name: "geometry_msgs/msg/Twist"
  gz_type_name: "gz.msgs.Twist"
  direction: ROS_TO_GZ

- ros_topic_name: "/scan"
  gz_topic_name: "/scan"
  ros_type_name: "sensor_msgs/msg/LaserScan"
  gz_type_name: "gz.msgs.LaserScan"
  direction: GZ_TO_ROS

- ros_topic_name: "/imu/data"
  gz_topic_name: "/imu/data"
  ros_type_name: "sensor_msgs/msg/Imu"
  gz_type_name: "gz.msgs.IMU"
  direction: GZ_TO_ROS
```

---

## 4. Executando o Launch File Completo

O launch file [`gazebo_sim.launch.py`](../rover_gazebo_ros2/launch/gazebo_sim.launch.py) orquestra a subida de todos os processos:

```bash
ros2 launch rover_gazebo_ros2 gazebo_sim.launch.py
```

---

## 🧪 Laboratório Prático 06

**Desafio**: 
1. Abra o arquivo do mundo [`worlds/blondel_stairs.sdf`](../rover_gazebo_ros2/worlds/blondel_stairs.sdf) e adicione um corrimão de aço e uma rampa lateral de $15^\circ$ adjacente aos degraus de Blondel.
2. Inicie a simulação e compare o tempo gasto para o Rover subir a rampa vs transpor os 3 degraus de $17\text{ cm}$.
