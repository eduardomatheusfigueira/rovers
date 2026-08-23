"""
Nó de tração: converte velocidade desejada de roda em **esforço**, respeitando a
curva do motorredutor, a queda de tensão do pack e o limite térmico.

Sem este nó o `ros2_control` comandaria velocidade e o Gazebo entregaria qualquer
torque até o limite da junta — o motor simulado teria torque de stall a 1,5 m/s.
A margem de torque de 1,61 calculada em `02_Engenharia/07` só é de fato testada
na simulação porque ela passa por aqui.

Publica também SOC, corrente, tensão e temperatura, que alimentam o supervisor e
o registrador de telemetria.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, String

from .cinematica_4ws import IDS
from .motor_dc import ControleTracao, MotorCC, PackBateria, Termica


class NoTracao(Node):
    def __init__(self) -> None:
        super().__init__("tracao")

        self.declare_parameter("reducao", 172.0)
        self.declare_parameter("kv_rpm_por_volt", 1000.0)
        self.declare_parameter("resistencia_motor", 1.10)
        self.declare_parameter("corrente_vazio", 0.35)
        self.declare_parameter("eficiencia_reducao", 0.72)
        self.declare_parameter("limite_corrente", 20.0)
        self.declare_parameter("consumo_auxiliar_w", 6.5)
        self.declare_parameter("frequencia_hz", 200.0)
        self.declare_parameter("kp", 4.0)
        self.declare_parameter("ki", 12.0)

        p = self.get_parameter
        self.motor = MotorCC(
            kv_rpm_por_volt=p("kv_rpm_por_volt").value,
            resistencia=p("resistencia_motor").value,
            corrente_vazio=p("corrente_vazio").value,
            reducao=p("reducao").value,
            eficiencia_reducao=p("eficiencia_reducao").value,
            limite_corrente=p("limite_corrente").value,
        )
        self.pack = PackBateria()
        self.termica = {w: Termica(resistencia=p("resistencia_motor").value) for w in IDS}
        self.controle = {w: ControleTracao(self.motor, p("kp").value, p("ki").value)
                         for w in IDS}
        self.freq = p("frequencia_hz").value
        self.consumo_aux = p("consumo_auxiliar_w").value

        self.desejada = {w: 0.0 for w in IDS}
        self.medida = {w: 0.0 for w in IDS}
        self.fator_torque = 1.0
        self.corrente_total = 0.0

        self.pub_esforco = self.create_publisher(
            Float64MultiArray, "/tracao_controller/commands", 10)
        self.pub_eletrico = self.create_publisher(Float64MultiArray, "~/eletrico", 10)
        self.pub_estado = self.create_publisher(String, "~/estado", 10)

        self.create_subscription(Float64MultiArray, "/tracao/velocidade_desejada",
                                 self._on_desejada, 10)
        self.create_subscription(JointState, "/joint_states", self._on_joints, 20)
        self.create_subscription(Float64MultiArray, "/supervisor/fator_torque",
                                 self._on_fator, 10)

        self.create_timer(1.0 / self.freq, self._passo)
        self.get_logger().info(
            f"tração a {self.freq:.0f} Hz — motorredutor 1:{self.motor.reducao:.0f}, "
            f"stall {self.motor.torque_stall_saida:.2f} N·m, "
            f"vazio {self.motor.omega_vazio_saida:.2f} rad/s")

    def _on_desejada(self, msg: Float64MultiArray) -> None:
        for i, w in enumerate(IDS):
            if i < len(msg.data):
                self.desejada[w] = float(msg.data[i])

    def _on_joints(self, msg: JointState) -> None:
        indice = {n: i for i, n in enumerate(msg.name)}
        for w in IDS:
            j = indice.get(f"tracao_{w}")
            if j is not None and j < len(msg.velocity):
                self.medida[w] = msg.velocity[j]

    def _on_fator(self, msg: Float64MultiArray) -> None:
        if msg.data:
            self.fator_torque = float(msg.data[0])

    def _passo(self) -> None:
        dt = 1.0 / self.freq
        tensao = self.pack.tensao(self.corrente_total)

        esforcos, correntes = [], []
        for w in IDS:
            fator = self.fator_torque
            if self.termica[w].temperatura >= self.termica[w].limite:
                fator = 0.0          # proteção I²t por motor
            torque, corrente = self.controle[w].passo(
                self.desejada[w], self.medida[w], tensao, dt, fator)
            self.termica[w].passo(corrente, dt)
            esforcos.append(torque)
            correntes.append(corrente)

        self.corrente_total = sum(correntes)
        self.pack.consumir(tensao * self.corrente_total + self.consumo_aux, dt)

        m = Float64MultiArray(); m.data = [float(e) for e in esforcos]
        self.pub_esforco.publish(m)

        m = Float64MultiArray()
        m.data = [float(self.corrente_total), float(tensao), float(self.pack.soc),
                  float(self.pack.consumido_wh),
                  float(max(t.temperatura for t in self.termica.values())),
                  float(self.pack.taxa_c(self.corrente_total))]
        self.pub_eletrico.publish(m)

        disponivel = self.motor.torque_disponivel(
            max(abs(v) for v in self.medida.values()), tensao)
        exigido = max(abs(e) for e in esforcos)
        estado = String()
        estado.data = (f"I={self.corrente_total:.1f}A ({self.pack.taxa_c(self.corrente_total):.1f}C) "
                       f"V={tensao:.1f} SOC={self.pack.soc*100:.0f}% "
                       f"T={max(t.temperatura for t in self.termica.values()):.0f}C "
                       f"margem={disponivel/max(exigido, 1e-3):.2f}")
        self.pub_estado.publish(estado)


def main() -> None:
    rclpy.init()
    no = NoTracao()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
