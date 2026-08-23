# Módulo 04: Parâmetros e Reconfiguração Dinâmica de Engenharia
## Referência: Francisco Martín Rico (2022) — Capítulo 6

---

## 1. Fundamentação Teórica

### 1.1. O Sistema de Parâmetros do ROS 2
No ROS 2, parâmetros são valores de configuração atrelados individualmente a cada nó (não existe um servidor global de parâmetros como no ROS 1):
* **Tipos Suportados**: `bool`, `int`, `double`, `string`, arrays e dicionários de bytes.
* **Descritores e Validação**: Definição de limites mínimo/máximo (`floating_point_range`) e documentação de cada parâmetro diretamente no código.
* **Reconfiguração em Tempo de Execução**: Parâmetros podem ser alterados em tempo real via CLI, GUI (rqt) ou *callbacks* sem precisar reiniciar o nó ou recompilar o código.

---

## 2. Parâmetros Mestres do Rover Frugal em YAML

Criamos o arquivo central de configuração `config/rover_parameters.yaml` vinculado à nossa especificação de engenharia:

```yaml
/**:
  ros__parameters:
    geometria:
      wheelbase_m: 1.36               # Distância entre eixos (m)
      track_width_m: 1.44             # Bitola do veículo (m)
      r_wheel_max_m: 0.210            # Raio da roda de Blondel Phi 420mm
      r_wheel_hub_m: 0.065            # Raio do cubo C-STS (m)

    suspensao_csts:
      stiffness_kt: 10.3              # Rigidez da mola espiral C-STS (N·m/rad)
      damping_ct: 0.08                # Amortecimento viscoso torsional (N·s/rad)
      max_deflection_deg: 25.0        # Batente angular elástico (graus)

    escada_blondel:
      riser_e_m: 0.170                # Espelho do degrau NBR 9050 (17 cm)
      tread_p_m: 0.300                # Piso do degrau NBR 9050 (30 cm)

    seguranca:
      pitch_alarm_threshold_deg: 43.0 # Limiar de alarme de tombamento
      max_linear_speed_mps: 1.2       # Velocidade máxima em piso plano
```

---

## 3. Implementação Prática: Nó com Callback de Reconfiguração Dinâmica

Vamos implementar o nó `rover_parameter_tuning.py` com validação de parâmetros e recálculo dinâmico da cinemática:

```python
#!/usr/bin/env python3
"""
Módulo 04 - Gestão de Parâmetros e Reconfiguração Dinâmica
Autor: Baseado em Francisco Martín Rico (2022)
"""

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult, ParameterDescriptor, FloatingPointRange

class RoverParameterTuner(Node):
    def __init__(self):
        super().__init__('rover_parameter_tuner')

        # Descritor com limites físicos para a rigidez da mola C-STS
        kt_desc = ParameterDescriptor(
            description="Rigidez torsional da mola espiral C-STS em N·m/rad",
            floating_point_range=[FloatingPointRange(from_value=0.1, to_value=50.0, step=0.1)]
        )

        # Declarar parâmetros com valores padrão
        self.declare_parameter('geometria.wheelbase_m', 1.36)
        self.declare_parameter('geometria.r_wheel_max_m', 0.210)
        self.declare_parameter('suspensao_csts.stiffness_kt', 10.3, kt_desc)
        self.declare_parameter('seguranca.max_linear_speed_mps', 1.2)

        # Registrar callback de alteração dinâmica
        self.add_on_set_parameters_callback(self.parameters_callback)

        self.get_logger().info("⚙️ [RoverParameterTuner] Parâmetros declarados com sucesso.")

    def parameters_callback(self, params):
        for param in params:
            if param.name == 'suspensao_csts.stiffness_kt':
                if param.value <= 0.0:
                    self.get_logger().error("❌ Rigidez kt não pode ser negativa ou nula!")
                    return SetParametersResult(successful=False, reason="Rigidez deve ser > 0")
                self.get_logger().info(f"🔄 Rigidez C-STS atualizada para: {param.value:.2f} N·m/rad")

            elif param.name == 'geometria.r_wheel_max_m':
                self.get_logger().info(f"🔄 Diâmetro da roda reconfigurado para: {param.value*2000:.0f} mm")

        return SetParametersResult(successful=True)

def main(args=None):
    rclpy.init(args=args)
    node = RoverParameterTuner()
    rclpy.spin(node)
    rclpy.shutdown()
```

---

## 4. Comandos de Inspeção e Modificação via CLI

Com o nó em execução, você pode inspecionar e alterar parâmetros sem reiniciar o sistema:

```bash
# Listar todos os parâmetros do nó:
ros2 param list /rover_parameter_tuner

# Ler um parâmetro específico:
ros2 param get /rover_parameter_tuner suspensao_csts.stiffness_kt

# Alterar a rigidez da mola para 12.5 N·m/rad em tempo de execução:
ros2 param set /rover_parameter_tuner suspensao_csts.stiffness_kt 12.5

# Alternar a geometria para a roda de 300 mm:
ros2 param set /rover_parameter_tuner geometria.r_wheel_max_m 0.150
```

---

## 🧪 Laboratório Prático 04

**Desafio**: Adicione ao nó uma verificação da **Fórmula de Blondel**:
Sempre que os parâmetros `escada_blondel.riser_e_m` ou `escada_blondel.tread_p_m` forem alterados, o nó deve calcular $2E + P$ e recusar a alteração (`SetParametersResult(successful=False)`) caso o valor resultante fuja da faixa normativa de $63\text{ cm}$ a $65\text{ cm}$.
