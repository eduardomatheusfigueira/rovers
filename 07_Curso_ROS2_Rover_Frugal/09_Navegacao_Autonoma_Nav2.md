# Módulo 09: Navegação Autônoma Avançada com a Stack Nav2
## Referência: Francisco Martín Rico (2022) — Capítulo 11

---

## 1. Fundamentação Teórica

### 1.1. A Arquitetura do Navigation 2 (Nav2)
O **Nav2** é a stack de navegação autônoma de nível industrial do ROS 2, estruturada em nós de ciclo de vida (*Lifecycle Nodes*) e plugins modulares:

```
 [Meta de Navegação (Goal)] ──> [Nav2 BT Navigator]
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        [Global Planner (SmacPlanner)]         [Local Controller (RPP)]
        - Calcula a rota A* no mapa            - Segue o caminho em 4WS
        - Evita obstáculos estáticos           - Desvia de pedestres/obstáculos dinâmicos
```

* **Global Planner**: Encontra o caminho ótimo global no mapa (`SmacPlanner` ou `NavFnPlanner`).
* **Local Controller**: Gera comandos `/cmd_vel` respeitando a aceleração, a curvatura e os limites das 4 rodas de raios curvos (`RegulatedPurePursuitController` ou `DWBController`).
* **Recovery Behaviors**: Manobras de escape caso o robô fique encurralado (Giro 4WS `spin_turn`, recuo ou pausa de desobstrução).

---

## 2. Configuração do Nav2 para Veículo 4WS (`nav2_params.yaml`)

```yaml
controller_server:
  ros__parameters:
    use_sim_time: True
    controller_plugins: ["FollowPath"]

    FollowPath:
      plugin: "nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController"
      desired_linear_vel: 0.8          # Velocidade de cruzeiro (m/s)
      lookahead_dist: 0.6              # Distância de antecipação (m)
      min_lookahead_dist: 0.3
      max_lookahead_dist: 1.2
      use_velocity_scaled_lookahead_dist: true
      transform_tolerance: 0.2
      use_approach_linear_velocity_scaling: true
      max_angular_accel: 2.0
      max_linear_accel: 1.5

global_costmap:
  global_costmap:
    ros__parameters:
      use_sim_time: True
      footprint: "[ [0.75, 0.80], [0.75, -0.80], [-0.75, -0.80], [-0.75, 0.80] ]"
      resolution: 0.05
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.95
```

---

## 3. Programando Navegação Autônoma em Python com `SimpleCommander`

Vamos criar o script `rover_delivery_navigator.py` para despachar o Rover até a porta do Departamento de TI:

```python
#!/usr/bin/env python3
"""
Módulo 09 - Despachante Autônomo com Nav2 Simple Commander
Autor: Baseado em Francisco Martín Rico (2022)
"""

import rclpy
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from geometry_msgs.msg import PoseStamped

def main():
    rclpy.init()
    nav = BasicNavigator()

    # 1. Definir Pose Inicial
    initial_pose = PoseStamped()
    initial_pose.header.frame_id = 'map'
    initial_pose.header.stamp = nav.get_clock().now().to_msg()
    initial_pose.pose.position.x = 0.0
    initial_pose.pose.position.y = 0.0
    initial_pose.pose.orientation.w = 1.0
    nav.setInitialPose(initial_pose)

    # 2. Aguardar ativação completa do Nav2
    nav.waitUntilNav2Active()

    # 3. Criar Meta: Porta da Sala da TI (X = 14.5m, Y = 6.2m)
    goal_pose = PoseStamped()
    goal_pose.header.frame_id = 'map'
    goal_pose.header.stamp = nav.get_clock().now().to_msg()
    goal_pose.pose.position.x = 14.5
    goal_pose.pose.position.y = 6.2
    goal_pose.pose.orientation.w = 1.0

    print("🚀 [Nav2] Enviando Rover para a Sala de TI...")
    nav.goToPose(goal_pose)

    # 4. Monitoramento do Feedback
    while not nav.isTaskComplete():
        feedback = nav.getFeedback()
        if feedback:
            print(f"⏱️ Distância restante: {feedback.distance_remaining:.2f} m | Tempo restante: {feedback.estimated_time_remaining.sec}s")

    # 5. Resultado
    result = nav.getResult()
    if result == TaskResult.SUCCEEDED:
        print("✅ [SUCESSO] Rover chegou com segurança à Sala de TI!")
    else:
        print("❌ [FALHA] Falha na navegação autônoma.")

    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

---

## 🧪 Laboratório Prático 09

**Desafio**: Insira um pedestre simulado (obstáculo dinâmico) no corredor durante a navegação do Rover. Observe como o `RegulatedPurePursuitController` recalcula os ângulos 4WS e desvia suavemente sem parar o veículo.
