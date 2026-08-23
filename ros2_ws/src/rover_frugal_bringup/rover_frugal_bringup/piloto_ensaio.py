"""
Piloto automático dos ensaios em simulação.

Executa um perfil de comandos determinístico (aproximação, engate, subida) para
que a corrida seja **repetível**: comparar previsão e simulação exige que o
comando de entrada seja o mesmo em todas as execuções, o que um piloto humano
não consegue garantir.
"""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool, String


class PilotoEnsaio(Node):
    def __init__(self) -> None:
        super().__init__("piloto_ensaio")
        self.declare_parameter("velocidade_aproximacao", 0.35)
        self.declare_parameter("velocidade_escada", 0.25)
        self.declare_parameter("distancia_aproximacao_s", 6.0)
        self.declare_parameter("duracao_subida_s", 40.0)
        self.declare_parameter("modo", "stair")

        self.pub_cmd = self.create_publisher(Twist, "/cmd_vel", 10)
        self.pub_modo = self.create_publisher(String, "/cinematica_4ws/modo", 10)
        self.pub_piso = self.create_publisher(Bool, "/supervisor/piso_seco", 10)

        self.t = 0.0
        self.fase = "preparar"
        self.create_timer(0.05, self._passo)

    def _passo(self) -> None:
        self.t += 0.05
        p = self.get_parameter

        if self.fase == "preparar":
            self.pub_modo.publish(String(data=p("modo").value))
            self.pub_piso.publish(Bool(data=True))   # ensaio em piso seco
            if self.t > 2.0:
                self.fase = "aproximar"
                self.get_logger().info("aproximação iniciada")
            return

        cmd = Twist()
        if self.fase == "aproximar":
            cmd.linear.x = p("velocidade_aproximacao").value
            if self.t > 2.0 + p("distancia_aproximacao_s").value:
                self.fase = "subir"
                self.get_logger().info("engate na escada — velocidade de escada")
        elif self.fase == "subir":
            cmd.linear.x = p("velocidade_escada").value
            if self.t > 2.0 + p("distancia_aproximacao_s").value + p("duracao_subida_s").value:
                self.fase = "parar"
                self.get_logger().info("ensaio concluído")
        self.pub_cmd.publish(cmd)


def main() -> None:
    rclpy.init()
    no = PilotoEnsaio()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
