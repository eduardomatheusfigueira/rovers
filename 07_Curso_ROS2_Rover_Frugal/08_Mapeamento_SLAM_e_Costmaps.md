# Módulo 08: Mapeamento, Cartografia (SLAM) e Camadas de Costmaps
## Referência: Francisco Martín Rico (2022) — Capítulo 10

---

## 1. Fundamentação Teórica

### 1.1. SLAM (Simultaneous Localization and Mapping)
O **SLAM** permite ao Rover construir o mapa de um ambiente desconhecido enquanto simultaneamente estima sua posição nele:
* **`slam_toolbox`**: Pacote padrão moderno no ROS 2 para ambientes de média e grande escala (como o campus Itaipu Parquetec), superando o antigo Gmapping em robustez de fechamento de laço (*Loop Closure*).
* **Entradas**: LaserScan 2D (`/scan`) + Odometria filtrada (`/odometry/filtered`).
* **Saída**: Grade de Ocupação 2D (`nav_msgs/msg/OccupancyGrid`) no tópico `/map` + Transformada dinâmica `map -> odom`.

---

## 2. Configuração do SLAM Toolbox (`slam_config.yaml`)

```yaml
slam_toolbox:
  ros__parameters:
    solver_plugin: solver_plugins::CeresSolver
    ceres_linear_solver: SPARSE_NORMAL_CHOLESKY
    ceres_preconditioner: SCHUR_JACOBI
    ceres_trust_strategy: LEVENBERG_MARQUARDT
    
    # Frames
    odom_frame: odom
    map_frame: map
    base_frame: base_footprint
    scan_topic: /scan
    use_map_saver: true
    mode: mapping # Modo Mapeamento Online

    # Resolução do Mapa
    resolution: 0.05               # 5 cm por pixel
    max_laser_range: 12.0          # Alcance máximo do LiDAR
    minimum_time_interval: 0.2     # Atualização a cada 200 ms
    transform_timeout: 0.2
    tf_buffer_duration: 30.0
    
    # Fechamento de Laço (Loop Closure)
    do_loop_closing: true
    loop_search_maximum_distance: 5.0
```

---

## 3. Mapeando o Campus Parquetec na Prática

1. **Iniciar a Simulação no Gazebo**:
   ```bash
   ros2 launch rover_gazebo_ros2 gazebo_sim.launch.py
   ```

2. **Iniciar o Nó de SLAM**:
   ```bash
   ros2 launch slam_toolbox online_async_launch.py slam_params_file:=config/slam_config.yaml use_sim_time:=True
   ```

3. **Abrir o RViz2 e Guiar o Rover**:
   ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard
   ```
   * Adicione o display **Map** assinando o tópico `/map`.
   * Conduza o robô pelos corredores, rampa e em direção à escada de Blondel.

4. **Salvar o Mapa Gerado**:
   ```bash
   ros2 run nav2_map_server map_saver_cli -f ~/rover_ws/maps/parquetec_ti_map
   ```
   * Gera os arquivos `parquetec_ti_map.yaml` e `parquetec_ti_map.pgm`.

---

## 🧪 Laboratório Prático 08

**Desafio**: Realize uma volta completa no circuito térreo $\to$ escadaria $\to$ sala da TI e verifique se o algoritmo executou o fechamento de laço (*Loop Closure*) com erro residual menor que $5\text{ cm}$.
