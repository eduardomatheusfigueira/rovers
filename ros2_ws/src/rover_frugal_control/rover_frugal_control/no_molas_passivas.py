"""Nó que aplica a lei de mola nas oito juntas passivas do rover."""

from __future__ import annotations

import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

from .cinematica_4ws import IDS
from .molas_passivas import MolaLinear, MolaTorsional


class NoMolasPassivas(Node):
    #: Ordem das juntas no vetor de comando do controlador de esforço.
    ORDEM = [f"susp_{w}" for w in IDS] + [f"csts_{w}" for w in IDS]

    def __init__(self) -> None:
        super().__init__("molas_passivas")

        self.declare_parameter("rigidez_suspensao", 1000.0)
        self.declare_parameter("amortecimento_suspensao", 25.0)
        self.declare_parameter("curso_suspensao", 0.090)
        self.declare_parameter("rigidez_csts", 12.30)
        self.declare_parameter("amortecimento_csts", 0.08)
        self.declare_parameter("limite_csts_rad", math.radians(35.0))
        self.declare_parameter("frequencia_hz", 800.0)

        p = self.get_parameter
        self.susp = MolaLinear(p("rigidez_suspensao").value,
                               p("amortecimento_suspensao").value,
                               p("curso_suspensao").value)
        self.csts = MolaTorsional(p("rigidez_csts").value,
                                  p("amortecimento_csts").value,
                                  p("limite_csts_rad").value)
        freq = p("frequencia_hz").value

        self.posicao = {n: 0.0 for n in self.ORDEM}
        self.velocidade = {n: 0.0 for n in self.ORDEM}

        self.pub = self.create_publisher(
            Float64MultiArray, "/passivas_controller/commands", 10)
        self.pub_energia = self.create_publisher(
            Float64MultiArray, "~/energia_csts", 10)
        self.create_subscription(JointState, "/joint_states", self._on_joints, 10)
        self.create_timer(1.0 / freq, self._passo)

        self.get_logger().info(
            f"molas passivas a {freq:.0f} Hz — suspensão {self.susp.rigidez:.0f} N/m "
            f"(curso {self.susp.curso*1000:.0f} mm, afundamento estático "
            f"{self.susp.afundamento_estatico(98.4/4)*1000:.0f} mm), "
            f"C-STS {self.csts.rigidez:.2f} N·m/rad")

    def _on_joints(self, msg: JointState) -> None:
        for i, nome in enumerate(msg.name):
            if nome in self.posicao:
                self.posicao[nome] = msg.position[i]
                if i < len(msg.velocity):
                    self.velocidade[nome] = msg.velocity[i]

    def _passo(self) -> None:
        comandos = []
        for w in IDS:
            n = f"susp_{w}"
            comandos.append(self.susp.esforco(self.posicao[n], self.velocidade[n]))
        energias = []
        for w in IDS:
            n = f"csts_{w}"
            comandos.append(self.csts.esforco(self.posicao[n], self.velocidade[n]))
            energias.append(self.csts.energia(self.posicao[n]))

        m = Float64MultiArray(); m.data = [float(c) for c in comandos]
        self.pub.publish(m)
        m = Float64MultiArray(); m.data = [float(e) for e in energias]
        self.pub_energia.publish(m)


def main() -> None:
    rclpy.init()
    no = NoMolasPassivas()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
