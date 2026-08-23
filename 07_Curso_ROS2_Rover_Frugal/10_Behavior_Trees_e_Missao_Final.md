# Módulo 10: Orquestração de Missões com Árvores de Comportamento (Behavior Trees)
## Referência: Francisco Martín Rico (2022) — Capítulo 12

---

## 1. Fundamentação Teórica

### 1.1. Máquinas de Estado Finitas (FSM) vs Árvores de Comportamento (BT)
Conforme enfatizado por Francisco Martín Rico (2022), para missões robóticas complexas (como transporte de cargas com travessia de escadas e portas estreitas), as tradicionais **FSMs** tornam-se incontroláveis e frágeis (*efeito espaguete*).

As **Behavior Trees (BT)** oferecem:
* **Alta Modularidade e Reusabilidade**: Nós podem ser recombinados sem alterar outros ramos.
* **Reatividade Contínua**: Condições de segurança (ex: nível de bateria, tombamento, pessoas no caminho) são avaliadas a cada *tick* (ex: 20 Hz).
* **Estrutura Hierárquica Intuitiva**:

```
                       [Sequence: Missão Completa TI]
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
       [Fallback: Checagem Bateria]      [Sequence: Ciclo de Transporte]
      ┌───────────────┴───────────────┐  ┌────────────┬────────────┬────────────┐
      ▼                               ▼  ▼            ▼            ▼            ▼
[Bateria > 14V?]             [Ir para Docagem] [Coletar] [Subir Escada] [Entregar]
```

### 1.2. Tipos de Nós em uma Behavior Tree
1. **Controle**:
   * `Sequence` ($\rightarrow$): Executa filhos sequencialmente. Retorna `SUCCESS` se todos sucederem; `FAILURE` no primeiro que falhar.
   * `Fallback` ($?$): Tenta o primeiro filho; se falhar, tenta o próximo (tratamento de contingências/recuperação).
   * `Parallel`: Executa múltiplos ramos simultaneamente (ex: navegar enquanto monitora a temperatura dos motores).
2. **Ação (*Action Node*)**: Executa comandos no robô (ex: `NavigateToPose`, `ClimbStairs`, `LockBrakes`).
3. **Condição (*Condition Node*)**: Checagens booleanas instantâneas (ex: `IsBatteryLow?`, `IsDoorOpen?`).

---

## 2. Árvore de Comportamento XML da Missão de Entrega do Notebook

Criamos o arquivo `config/mission_bt.xml`:

```xml
<root main_tree_to_execute="MainMissionTree">
  <BehaviorTree ID="MainMissionTree">
    <Sequence name="MissaoEntregaNotebookTI">
      
      <!-- 1. Checagem de Segurança da Bateria -->
      <Fallback name="GarantiaDeEnergia">
        <Condition ID="CheckBatteryOk" min_voltage="14.0"/>
        <Action ID="NavigateToChargingDock"/>
      </Fallback>

      <!-- 2. Coleta no Posto de Trabalho -->
      <Sequence name="Coleta">
        <Action ID="NavigateToPose" goal="0.0;0.0;0.0" name="IrParaPontoColeta"/>
        <Action ID="WaitForLaptopLoadConfirmation" timeout_sec="30.0"/>
      </Sequence>

      <!-- 3. Deslocamento até a Escada -->
      <Action ID="NavigateToPose" goal="12.0;0.0;0.0" name="IrParaBaseDaEscada"/>

      <!-- 4. Transposição da Escada de Blondel -->
      <Sequence name="EscaladaBlondel">
        <Action ID="SetDriveMode" mode="STAIR"/>
        <Action ID="ClimbBlondelStairsAction" steps="8" speed="0.35"/>
        <Action ID="SetDriveMode" mode="ACKERMANN"/>
      </Sequence>

      <!-- 5. Travessia de Porta Estreita e Entrega na TI -->
      <Sequence name="EntregaTI">
        <Action ID="SetDriveMode" mode="CRAB"/> <!-- Modo Caranguejo para porta estreita -->
        <Action ID="NavigateToPose" goal="18.5;4.2;0.0" name="EntrarSalaTI"/>
        <Action ID="SetDriveMode" mode="ACKERMANN"/>
        <Action ID="NotifyITTechnicianArrival"/>
      </Sequence>

      <!-- 6. Retorno à Base -->
      <Action ID="NavigateToPose" goal="0.0;0.0;0.0" name="RetornarABase"/>

    </Sequence>
  </BehaviorTree>
</root>
```

---

## 3. Implementação do Executor em Python com `py_trees`

```python
#!/usr/bin/env python3
"""
Módulo 10 - Executor de Behavior Tree em Python
Autor: Baseado em Francisco Martín Rico (2022)
"""

import rclpy
import py_trees
from py_trees.trees import BehaviourTree
from py_trees.behaviour import Behaviour
from py_trees.common import Status

class CheckBatteryBehaviour(Behaviour):
    def __init__(self, name="CheckBattery"):
        super().__init__(name)

    def update(self):
        battery_v = 15.8 # Leitura simulada
        if battery_v >= 14.0:
            print("🔋 [BT] Bateria OK para a missão!")
            return Status.SUCCESS
        else:
            print("⚠️ [BT] Bateria fraca! Abortando para recarga.")
            return Status.FAILURE

def create_mission_tree():
    root = py_trees.composites.Sequence(name="MissaoTI", memory=True)
    check_bat = CheckBatteryBehaviour()
    root.add_child(check_bat)
    return root

def main():
    rclpy.init()
    tree = BehaviourTree(create_mission_tree())
    tree.setup(timeout=15)
    tree.tick()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

---

## 🧪 Laboratório Prático 10

**Desafio**: Execute a árvore de missão completa no Gazebo Sim e simule uma queda repentina de tensão no meio da escadaria. Observe como a árvore cancela a ação de subida e aciona o ramo de recuo seguro (*Fallback*).
