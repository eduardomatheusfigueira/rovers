"""
Registrador de telemetria: grava em CSV **as mesmas colunas** que o gêmeo digital
3D exporta e que o firmware embarcado publica.

É isso que torna o ensaio ENS-06 possível: a mesma planilha compara a previsão do
modelo analítico, a simulação em Gazebo e a medição de campo, sem conversão de
formato no meio do caminho.
"""

from __future__ import annotations

import csv
import math
import os
from datetime import datetime

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from std_msgs.msg import Float64MultiArray

IDS = ("FL", "FR", "RL", "RR")

COLUNAS = [
    "t", "x", "y", "z", "velocidade", "arfagem_deg", "rolagem_deg",
    "carga_vert_g", "carga_long_g",
    "corrente_A", "torque_max_Nm", "margem_torque",
    "susp_FL_mm", "susp_FR_mm", "susp_RL_mm", "susp_RR_mm",
    "csts_FL_deg", "csts_FR_deg", "csts_RL_deg", "csts_RR_deg",
    "energia_csts_J", "estercamento_max_deg",
]

G = 9.80665
#: Constantes da cadeia de tração (02_Engenharia/07): I = T / (Kt·i·η)
KT, REDUCAO, ETA = 0.009549, 172.0, 0.72
TORQUE_STALL = 12.49


class Registrador(Node):
    def __init__(self) -> None:
        super().__init__("registrador_telemetria")
        self.declare_parameter("arquivo", "")
        self.declare_parameter("frequencia_hz", 20.0)

        caminho = self.get_parameter("arquivo").value
        if not caminho:
            carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = os.path.join(os.getcwd(), f"telemetria_gazebo_{carimbo}.csv")
        self.caminho = caminho
        self.arquivo = open(caminho, "w", newline="", encoding="utf-8")
        self.csv = csv.DictWriter(self.arquivo, fieldnames=COLUNAS)
        self.csv.writeheader()

        self.dados = {c: 0.0 for c in COLUNAS}
        self.t0 = None
        self.pico_vertical = 0.0

        self.create_subscription(Imu, "/imu", self._on_imu, 20)
        self.create_subscription(JointState, "/joint_states", self._on_joints, 20)
        self.create_subscription(Odometry, "/odom_verdade", self._on_odom, 20)
        self.create_subscription(Float64MultiArray, "/molas_passivas/energia_csts",
                                 self._on_energia, 10)

        self.create_timer(1.0 / self.get_parameter("frequencia_hz").value, self._gravar)
        self.get_logger().info(f"registrando telemetria em {caminho}")

    def _on_imu(self, msg: Imu) -> None:
        q = msg.orientation
        seno = max(-1.0, min(1.0, 2.0 * (q.w * q.y - q.z * q.x)))
        self.dados["arfagem_deg"] = math.degrees(math.asin(seno))
        self.dados["rolagem_deg"] = math.degrees(math.atan2(
            2.0 * (q.w * q.x + q.y * q.z), 1.0 - 2.0 * (q.x * q.x + q.y * q.y)))
        a = msg.linear_acceleration
        # Aceleração sentida pela carga, descontando a gravidade projetada
        self.dados["carga_vert_g"] = (a.z - G * math.cos(math.radians(
            self.dados["arfagem_deg"]))) / G
        self.dados["carga_long_g"] = a.x / G
        self.pico_vertical = max(self.pico_vertical, abs(self.dados["carga_vert_g"]))

    def _on_joints(self, msg: JointState) -> None:
        indice = {n: i for i, n in enumerate(msg.name)}
        torques = []
        for w in IDS:
            if f"susp_{w}" in indice:
                self.dados[f"susp_{w}_mm"] = msg.position[indice[f"susp_{w}"]] * 1000.0
            if f"csts_{w}" in indice:
                self.dados[f"csts_{w}_deg"] = math.degrees(msg.position[indice[f"csts_{w}"]])
            if f"tracao_{w}" in indice and indice[f"tracao_{w}"] < len(msg.effort):
                torques.append(abs(msg.effort[indice[f"tracao_{w}"]]))
        estercos = [abs(math.degrees(msg.position[indice[f"esterco_{w}"]]))
                    for w in IDS if f"esterco_{w}" in indice]
        if estercos:
            self.dados["estercamento_max_deg"] = max(estercos)
        if torques:
            t_max = max(torques)
            self.dados["torque_max_Nm"] = t_max
            self.dados["corrente_A"] = 4.0 * t_max / (KT * REDUCAO * ETA)
            self.dados["margem_torque"] = TORQUE_STALL / max(t_max, 1e-3)

    def _on_odom(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        v = msg.twist.twist.linear
        self.dados["x"], self.dados["y"], self.dados["z"] = p.x, p.y, p.z
        self.dados["velocidade"] = math.hypot(v.x, v.y)

    def _on_energia(self, msg: Float64MultiArray) -> None:
        self.dados["energia_csts_J"] = float(sum(msg.data))

    def _gravar(self) -> None:
        agora = self.get_clock().now().nanoseconds * 1e-9
        if self.t0 is None:
            self.t0 = agora
        self.dados["t"] = agora - self.t0
        self.csv.writerow({c: round(self.dados[c], 5) for c in COLUNAS})
        self.arquivo.flush()

    def destroy_node(self) -> bool:
        self.get_logger().info(
            f"pico de aceleração vertical na carga: {self.pico_vertical:.2f} g "
            f"(limite de projeto: 2,0 g) — {self.caminho}")
        self.arquivo.close()
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    no = Registrador()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
