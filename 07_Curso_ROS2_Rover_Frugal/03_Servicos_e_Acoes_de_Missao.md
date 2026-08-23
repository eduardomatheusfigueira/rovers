# Módulo 03: Serviços e Ações Assíncronas para Manobras e Escadas
## Referência: Francisco Martín Rico (2022) — Capítulos 4 e 5

---

## 1. Fundamentação Teórica

### 1.1. Serviços (Client-Service: Request-Response)
Diferente dos tópicos (fluxo contínuo), os **Serviços** implementam um padrão síncrono ou assíncrono de **Requisição e Resposta pontual**:
* **Uso Ideal**: Configurações de estado, calibração de sensores (tara da IMU), travamento de freio ou mudança instantânea de modo de direção 4WS.
* **Características**: Um único servidor atende requisições de múltiplos clientes.

### 1.2. Ações (Action Servers & Clients: Long-Running & Preemptable)
Para operações que demandam tempo prolongado para serem concluídas (como navegar $50\text{ m}$ ou subir uma escadaria de 8 degraus de Blondel), tópicos ou serviços são inadequados:
* **Goal**: O cliente solicita o objetivo inicial.
* **Feedback Contínuo**: O servidor informa o progresso intermediário (ex: "degrau 2 de 8 concluído, inclinação atual = $24^\circ$").
* **Result**: O servidor notifica o sucesso ou falha ao final.
* **Preemptabilidade / Cancelamento**: O cliente pode cancelar a ação a qualquer momento (ex: botão de emergência acionado ou risco iminente de tombamento).

```
 [Action Client] ──── Goal: Subir 8 Degraus ───> [Action Server: StairClimber]
                 <── Feedback: Degrau 1/8, 2/8 ──
                 <── Result: Sucesso (18.4s) ────
```

---

## 2. Implementação do Serviço: Mudança de Modo 4WS

Definição da interface `srv/SetDriveMode.srv`:
```text
string mode   # "ackermann", "crab", "spin", "stair"
---
bool success
string message
```

### Código do Servidor de Serviço em Python (`rover_mode_service.py`):
```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool

class RoverModeManager(Node):
    def __init__(self):
        super().__init__('rover_mode_manager')
        self.current_mode = "ACKERMANN"
        
        # Criar Servidor de Serviço
        self.srv = self.create_service(SetBool, '/rover/set_stair_mode', self.set_mode_callback)
        self.get_logger().info("🛠️ [RoverModeManager] Servidor de modos 4WS pronto.")

    def set_mode_callback(self, request, response):
        if request.data:
            self.current_mode = "STAIR_CLIMBING"
            response.success = True
            response.message = "✅ Modo ESCADA (Stair) ativado com sucesso: eixos sincronizados a 120°."
        else:
            self.current_mode = "ACKERMANN"
            response.success = True
            response.message = "✅ Modo ACKERMANN padrão reativado."
            
        self.get_logger().info(f"Modo alterado para: {self.current_mode}")
        return response

def main(args=None):
    rclpy.init(args=args)
    node = RoverModeManager()
    rclpy.spin(node)
    rclpy.shutdown()
```

---

## 3. Implementação da Ação: Subir Escadaria de Blondel

Definição da interface `action/ClimbStairs.action`:
```text
# Goal
int32 target_steps       # Quantidade de degraus (ex: 3 ou 8)
float32 target_speed     # Velocidade de subida (ex: 0.4 m/s)
---
# Result
bool success
float32 total_time_sec
int32 completed_steps
---
# Feedback
int32 current_step
float32 current_pitch_deg
float32 csts_strain_percent
```

### Código do Action Server em Python (`stair_climbing_action_server.py`):
```python
#!/usr/bin/env python3
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from geometry_msgs.msg import Twist

class StairClimbingActionServer(Node):
    def __init__(self):
        super().__init__('stair_climbing_action_server')
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info("🪜 [StairClimber] Action Server de Transposição de Blondel pronto!")

    def execute_climb(self, target_steps: int, speed: float):
        """
        Executa a sequência física de avanço sincronizado com os 3 raios curvos.
        """
        for step in range(1, target_steps + 1):
            self.get_logger().info(f"⬆️ Escalando degrau {step}/{target_steps} (E=17cm, P=30cm)...")
            
            # Avanço proporcional à rotação de 120 graus do raio
            cmd = Twist()
            cmd.linear.x = speed
            self.pub_cmd.publish(cmd)
            time.sleep(1.8) # Tempo de engate de 1 raio de Blondel

        # Parar no patamar superior
        cmd.linear.x = 0.0
        self.pub_cmd.publish(cmd)
        self.get_logger().info("🏁 Patamar superior atingido com sucesso!")
```

---

## 🧪 Laboratório Prático 03

**Desafio**:
1. Inicie o nó do servidor de ação no terminal.
2. Em outro terminal, envie uma meta de transposição de **3 degraus de Blondel** usando a CLI do ROS 2:
   ```bash
   ros2 service call /rover/set_stair_mode std_srvs/srv/SetBool "{data: true}"
   ```
3. Teste o cancelamento da ação simulando uma inclinação lateral perigosa (*Roll* $> 15^\circ$).
