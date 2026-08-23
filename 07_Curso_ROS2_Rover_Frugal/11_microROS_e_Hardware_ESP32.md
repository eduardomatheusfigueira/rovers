# Módulo 11: Integração com Hardware Físico via micro-ROS no ESP32
## Ponte de Comunicação Embarcada de Baixo Custo para os 4 Motores e Servos 4WS

---

## 1. Fundamentação Teórica

### 1.1. O que é o micro-ROS?
O **micro-ROS** leva o ROS 2 diretamente para microcontroladores de baixo custo (como o **ESP32**), permitindo que o firmware embarcado participe nativamente do Grafo Computacional do ROS 2 como nós legítimos, publicando e assinando tópicos sem necessidade de protocolos seriais proprietários (como Firmata ou texto serial simples):

```
 ┌────────────────────────────────────────────────────────┐
 │           Computador / Raspberry Pi 4 (ROS 2)          │
 │              - micro-ROS Agent (DDS Bridge)            │
 └───────────────────────────▲────────────────────────────┘
                             │ Wi-Fi UDP / Serial UART
 ┌───────────────────────────▼────────────────────────────┐
 │                  ESP32 (micro-ROS Client)              │
 │  - Nó 1: Leitura de Encoders das 4 Rodas (100 Hz)      │
 │  - Nó 2: Controle PWM dos 4 Motores de Tração 4WD      │
 │  - Nó 3: Controle de Posição dos 4 Servos 4WS          │
 └────────────────────────────────────────────────────────┘
```

---

## 2. Firmware em C++ para ESP32 (ESP-IDF / Arduino IDE)

Código do cliente micro-ROS para controle das 4 rodas e esterçamento 4WS:

```cpp
#include <micro_ros_arduino.h>
#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <geometry_msgs/msg/twist.h>
#include <sensor_msgs/msg/joint_state.h>

rcl_subscription_t subscriber_cmd_vel;
geometry_msgs__msg__Twist msg_cmd_vel;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// Callback de Comandos de Velocidade do ROS 2
void cmd_vel_callback(const void * msgin) {
  const geometry_msgs__msg__Twist * msg = (const geometry_msgs__msg__Twist *)msgin;
  float vx = msg->linear.x;
  float omega = msg->angular.z;

  // Controle de PWM dos motores de tração
  int pwm_val = constrain(abs(vx) * 255.0, 0, 255);
  // Acionar Ponte H (L298N / BTS7960)...
}

void setup() {
  set_microros_transports(); // Serial ou Wi-Fi
  allocator = rcl_get_default_allocator();

  // Inicializar micro-ROS
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "rover_esp32_hardware", "", &support);

  // Criar Assinante /cmd_vel
  rclc_subscription_init_default(
    &subscriber_cmd_vel,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    "/cmd_vel"
  );

  rclc_executor_init(&executor, &support.context, 1, &allocator);
  rclc_executor_add_subscription(&executor, &subscriber_cmd_vel, &msg_cmd_vel, &cmd_vel_callback, ON_NEW_DATA);
}

void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
  delay(10);
}
```

---

## 3. Executando o micro-ROS Agent no Linux/ROS 2

Para conectar o ROS 2 ao ESP32 via Serial USB:

```bash
# Iniciar o Agente micro-ROS:
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200
```

Ou via **Wi-Fi UDP** (sem fios):
```bash
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
```

Assim que o ESP32 conecta, os tópicos do hardware físico surgem instantaneamente no seu `ros2 topic list`!

---

## 🧪 Laboratório Prático 11

**Desafio Final do Curso**: 
1. Conecte o ESP32 à bancada com os 4 motores DC de tração e os 4 servomotores de esterçamento.
2. Inicie o `micro_ros_agent`.
3. Execute o nó de navegação autônoma do Módulo 09 (`rover_delivery_navigator.py`) e observe o Rover real executando a trajetória física no laboratório!
