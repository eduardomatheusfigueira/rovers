"""
Nó de cinemática 4WS: /cmd_vel  →  comandos de esterçamento e tração.

Implementa o que a análise de R2 mostrou ser obrigatório e que um nó ingênuo de
`cmd_vel` não faz:

* **Reconfiguração de modo com o veículo parado.** δs = 2 significa que o rover
  não é holonômico: trocar de Ackermann para caranguejo exige reorientar as
  rodas. O nó freia, reorienta, e só então libera a tração.
* **Limitação de taxa dos servos.** O comando de posição respeita a velocidade
  máxima do servo; mandar um degrau de 90° faz o servo saturar e o veículo
  arrastar.
* **Publicação do resíduo de deslizamento.** É a métrica que denuncia
  descoordenação de esterçamento em campo.
"""

from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, String

from .cinematica_4ws import IDS, MODOS, Geometria, resolver, residuo_deslizamento

POSES_MODO = {
    "ackermann": {w: 0.0 for w in IDS},
    "stair": {w: 0.0 for w in IDS},
}


class NoCinematica4WS(Node):
    def __init__(self) -> None:
        super().__init__("cinematica_4ws")

        self.declare_parameter("entre_eixos", 0.690)
        self.declare_parameter("bitola", 0.600)
        self.declare_parameter("raio_roda", 0.210)
        self.declare_parameter("limite_estercamento_rad", math.radians(55.0))
        self.declare_parameter("velocidade_servo_rad_s", 5.24)
        self.declare_parameter("velocidade_maxima", 1.20)
        self.declare_parameter("velocidade_escada", 0.25)
        self.declare_parameter("frequencia_hz", 200.0)
        self.declare_parameter("timeout_cmd_vel_s", 0.30)

        p = self.get_parameter
        self.geo = Geometria(
            entre_eixos=p("entre_eixos").value,
            bitola=p("bitola").value,
            raio_roda=p("raio_roda").value,
            limite_estercamento=p("limite_estercamento_rad").value,
        )
        self.vel_servo = p("velocidade_servo_rad_s").value
        self.freq = p("frequencia_hz").value
        self.timeout = p("timeout_cmd_vel_s").value

        self.modo = "ackermann"
        self.modo_alvo = "ackermann"
        self.reconfigurando = False
        self.angulos = {w: 0.0 for w in IDS}
        self.cmd = Twist()
        self.ultimo_cmd = self.get_clock().now()

        self.pub_esterco = self.create_publisher(
            Float64MultiArray, "/esterco_controller/commands", 10)
        # A cinemática publica VELOCIDADE DESEJADA de roda; quem converte em
        # esforço é o nó `tracao`, que aplica a curva do motorredutor. Comandar
        # o controlador de junta direto daria ao motor simulado torque de stall
        # em qualquer rotação.
        self.pub_tracao = self.create_publisher(
            Float64MultiArray, "/tracao/velocidade_desejada", 10)
        self.pub_residuo = self.create_publisher(Float64MultiArray, "~/residuo", 10)
        self.pub_estado = self.create_publisher(String, "~/estado", 10)

        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self.create_subscription(String, "~/modo", self._on_modo, 10)
        self.create_subscription(JointState, "/joint_states", self._on_joints, 10)

        self.create_timer(1.0 / self.freq, self._passo)
        self.get_logger().info(
            f"cinemática 4WS a {self.freq:.0f} Hz — "
            f"L={self.geo.entre_eixos:.3f} m, W={self.geo.bitola:.3f} m, "
            f"r={self.geo.raio_roda:.3f} m, |β|max={math.degrees(self.geo.limite_estercamento):.0f}°")

    # ---------------------------------------------------------------- callbacks
    def _on_cmd_vel(self, msg: Twist) -> None:
        self.cmd = msg
        self.ultimo_cmd = self.get_clock().now()

    def _on_modo(self, msg: String) -> None:
        if msg.data not in MODOS:
            self.get_logger().warn(f"modo desconhecido: {msg.data}")
            return
        if msg.data != self.modo:
            self.modo_alvo = msg.data
            self.reconfigurando = True
            self.get_logger().info(
                f"reconfigurando {self.modo} → {msg.data}: parando para reorientar "
                f"as rodas (δs = 2, o rover não é holonômico)")

    def _on_joints(self, msg: JointState) -> None:
        for wid in IDS:
            nome = f"esterco_{wid}"
            if nome in msg.name:
                self.angulos[wid] = msg.position[msg.name.index(nome)]

    # ------------------------------------------------------------------- laço
    def _passo(self) -> None:
        dt = 1.0 / self.freq
        idade = (self.get_clock().now() - self.ultimo_cmd).nanoseconds * 1e-9
        vivo = idade < self.timeout

        vx = self.cmd.linear.x if vivo else 0.0
        vy = self.cmd.linear.y if vivo else 0.0
        wz = self.cmd.angular.z if vivo else 0.0

        v_max = (self.get_parameter("velocidade_escada").value
                 if self.modo in ("stair",)
                 else self.get_parameter("velocidade_maxima").value)
        norma = math.hypot(vx, vy)
        if norma > v_max:
            vx, vy = vx * v_max / norma, vy * v_max / norma

        # Durante a reconfiguração a tração fica zerada: reorientar rodas
        # carregadas e girando é exatamente o que produz arrasto e desgaste.
        if self.reconfigurando:
            alvo = resolver(self.geo, 0.3, 0.3 if self.modo_alvo == "crab" else 0.0,
                            0.6 if self.modo_alvo == "spin" else 0.0, self.modo_alvo)
            self._publicar(alvo.angulos, {w: 0.0 for w in IDS})
            erro = max(abs(alvo.angulos[w] - self.angulos[w]) for w in IDS)
            if erro < math.radians(1.0):
                self.modo = self.modo_alvo
                self.reconfigurando = False
                self.get_logger().info(f"modo {self.modo} assentado")
            self._publicar_estado(vivo, 0.0)
            return

        cmd = resolver(self.geo, vx, vy, wz, self.modo)

        # Limitação de taxa: o servo tem velocidade finita
        limitados = {}
        for wid in IDS:
            passo_max = self.vel_servo * dt
            delta = cmd.angulos[wid] - self.angulos[wid]
            limitados[wid] = self.angulos[wid] + max(-passo_max, min(passo_max, delta))

        self._publicar(limitados, cmd.velocidades_rodas)
        self._publicar_estado(vivo, residuo_deslizamento(self.geo, cmd, vx, vy, wz),
                              cmd.saturado)

    # -------------------------------------------------------------- publicação
    def _publicar(self, angulos, velocidades) -> None:
        m = Float64MultiArray(); m.data = [float(angulos[w]) for w in IDS]
        self.pub_esterco.publish(m)
        m = Float64MultiArray(); m.data = [float(velocidades[w]) for w in IDS]
        self.pub_tracao.publish(m)

    def _publicar_estado(self, vivo: bool, residuo: float, saturado: bool = False) -> None:
        m = Float64MultiArray(); m.data = [float(residuo)]
        self.pub_residuo.publish(m)
        estado = String()
        estado.data = (f"modo={self.modo} reconfigurando={self.reconfigurando} "
                       f"enlace={'ok' if vivo else 'PERDIDO'} "
                       f"estercamento_saturado={saturado} residuo={residuo:.4f}")
        self.pub_estado.publish(estado)


def main() -> None:
    rclpy.init()
    no = NoCinematica4WS()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
