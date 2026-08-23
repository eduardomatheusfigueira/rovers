"""Nó do supervisor de segurança (máquina de estados de 02_Engenharia/08)."""

from __future__ import annotations

import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from std_msgs.msg import Bool, Float64MultiArray, String

from .supervisor import Entradas, Limites, ModeloTermico, Supervisor


class NoSupervisor(Node):
    def __init__(self) -> None:
        super().__init__("supervisor")

        self.declare_parameter("pitch_critico_plano_deg", 35.0)
        self.declare_parameter("pitch_critico_escada_deg", 52.0)
        self.declare_parameter("roll_critico_deg", 30.0)
        self.declare_parameter("timeout_failsafe_s", 0.30)
        self.declare_parameter("frequencia_hz", 100.0)
        self.declare_parameter("resistencia_motor", 1.10)

        p = self.get_parameter
        self.sup = Supervisor(
            Limites(p("pitch_critico_plano_deg").value,
                    p("pitch_critico_escada_deg").value,
                    p("roll_critico_deg").value,
                    p("timeout_failsafe_s").value),
            ModeloTermico(resistencia=p("resistencia_motor").value),
        )
        self.entradas = Entradas()
        self.freq = p("frequencia_hz").value

        self.pub_estado = self.create_publisher(String, "~/estado", 10)
        self.pub_freio = self.create_publisher(Bool, "~/freio_dinamico", 10)
        self.pub_fator = self.create_publisher(Float64MultiArray, "~/fator_torque", 10)

        self.create_subscription(Imu, "/imu", self._on_imu, 20)
        self.create_subscription(JointState, "/joint_states", self._on_joints, 20)
        self.create_subscription(String, "/cinematica_4ws/estado", self._on_modo, 10)
        self.create_subscription(Bool, "~/rearme", self._on_rearme, 10)
        self.create_subscription(Bool, "~/piso_seco", self._on_piso, 10)

        self.create_timer(1.0 / self.freq, self._passo)
        self.get_logger().info(
            f"supervisor a {self.freq:.0f} Hz — limiar de arfagem: "
            f"{self.sup.lim.pitch_plano_deg:.0f}° em piso, "
            f"{self.sup.lim.pitch_escada_deg:.0f}° em escada "
            f"(a marcha de 3 raios leva o chassi a ~43° em subida normal)")

    def _on_imu(self, msg: Imu) -> None:
        q = msg.orientation
        seno = 2.0 * (q.w * q.y - q.z * q.x)
        seno = max(-1.0, min(1.0, seno))
        self.entradas.arfagem_deg = math.degrees(math.asin(seno))
        self.entradas.rolagem_deg = math.degrees(math.atan2(
            2.0 * (q.w * q.x + q.y * q.z), 1.0 - 2.0 * (q.x * q.x + q.y * q.y)))

    def _on_joints(self, msg: JointState) -> None:
        # Estimativa de corrente pelo esforço das juntas de tração.
        esforcos = [abs(e) for n, e in zip(msg.name, msg.effort) if n.startswith("tracao_")]
        if esforcos:
            # I = T / (Kt·i·η); os fatores vêm do dimensionamento em 02_Engenharia/07
            self.entradas.corrente_por_motor = max(esforcos) / (0.009549 * 172.0 * 0.72)

    def _on_modo(self, msg: String) -> None:
        for parte in msg.data.split():
            if parte.startswith("modo="):
                self.entradas.modo = parte.split("=", 1)[1]
            if parte.startswith("enlace="):
                self.entradas.idade_enlace_s = 0.0 if parte.endswith("ok") else 1.0

    def _on_rearme(self, msg: Bool) -> None:
        self.entradas.rearme_solicitado = msg.data

    def _on_piso(self, msg: Bool) -> None:
        self.entradas.piso_seco_confirmado = msg.data

    def _passo(self) -> None:
        s = self.sup.passo(self.entradas, 1.0 / self.freq)
        self.entradas.rearme_solicitado = False

        m = String()
        m.data = (f"{s.estado.value} | tracao={'liberada' if s.tracao_liberada else 'bloqueada'} "
                  f"| temp={self.sup.termico.temperatura:.0f}C "
                  f"| arfagem={self.entradas.arfagem_deg:.1f}deg"
                  + (" | " + "; ".join(s.alertas) if s.alertas else ""))
        self.pub_estado.publish(m)
        self.pub_freio.publish(Bool(data=s.freio_dinamico))
        f = Float64MultiArray(); f.data = [float(s.fator_torque)]
        self.pub_fator.publish(f)


def main() -> None:
    rclpy.init()
    no = NoSupervisor()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
