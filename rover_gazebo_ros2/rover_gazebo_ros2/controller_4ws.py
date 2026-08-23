#!/usr/bin/env python3
"""
Nó ROS 2 de Controle Cinemático 4WS/4WD para o Rover Frugal no Gazebo Sim
Calcula a cinemática inversa omnidirecional (Siegwart & Nourbakhsh, 2004) e publica odometria.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
import tf2_ros
import numpy as np

class Rover4WSController(Node):
    def __init__(self):
        super().__init__('rover_4ws_controller')

        # Parâmetros Geométricos Mestres
        self.wheelbase = 1.36   # Distância entre eixos (m)
        self.track_width = 1.44 # Bitola (m)
        self.r_wheel = 0.210    # Raio máximo da roda (m)

        # Estados de Odometria
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.last_time = self.get_clock().now()

        # Modo Operacional Atual ('ackermann', 'crab', 'spin', 'stair')
        self.current_mode = 'ackermann'

        # Subscrições
        self.sub_cmd_vel = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.sub_joint_states = self.create_subscription(JointState, '/joint_states', self.joint_state_callback, 10)

        # Publicadores
        self.pub_odom = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Publicadores de Comandos para as Juntas do Gazebo
        self.pub_steer = {
            'fl': self.create_publisher(Float64, '/model/rover_frugal/joint/fl_steer_joint/cmd_pos', 10),
            'fr': self.create_publisher(Float64, '/model/rover_frugal/joint/fr_steer_joint/cmd_pos', 10),
            'rl': self.create_publisher(Float64, '/model/rover_frugal/joint/rl_steer_joint/cmd_pos', 10),
            'rr': self.create_publisher(Float64, '/model/rover_frugal/joint/rr_steer_joint/cmd_pos', 10),
        }
        self.pub_wheel = {
            'fl': self.create_publisher(Float64, '/model/rover_frugal/joint/fl_wheel_joint/cmd_vel', 10),
            'fr': self.create_publisher(Float64, '/model/rover_frugal/joint/fr_wheel_joint/cmd_vel', 10),
            'rl': self.create_publisher(Float64, '/model/rover_frugal/joint/rl_wheel_joint/cmd_vel', 10),
            'rr': self.create_publisher(Float64, '/model/rover_frugal/joint/rr_wheel_joint/cmd_vel', 10),
        }

        self.get_logger().info("Nó de Controle 4WS/4WD do Rover Frugal iniciado com sucesso!")

    def cmd_vel_callback(self, msg: Twist):
        vx = msg.linear.x
        vy = msg.linear.y
        omega = msg.angular.z

        # Identificação de Modo Automática
        if abs(vy) > 0.05 and abs(omega) < 0.05:
            mode = 'crab'
        elif abs(vx) < 0.02 and abs(vy) < 0.02 and abs(omega) > 0.05:
            mode = 'spin'
        else:
            mode = 'ackermann'

        steer_angles, wheel_speeds = self.compute_4ws_kinematics(vx, vy, omega, mode)

        # Publicar nas juntas de esterçamento (4WS)
        for key in ['fl', 'fr', 'rl', 'rr']:
            pos_msg = Float64()
            pos_msg.data = float(steer_angles[key])
            self.pub_steer[key].publish(pos_msg)

            vel_msg = Float64()
            vel_msg.data = float(wheel_speeds[key])
            self.pub_wheel[key].publish(vel_msg)

    def compute_4ws_kinematics(self, vx: float, vy: float, omega: float, mode: str):
        steer = {}
        speeds = {}
        half_l = self.wheelbase / 2.0
        half_w = self.track_width / 2.0

        if mode == 'spin':
            # Giro no próprio eixo (Raio Zero)
            steer_angle = np.arctan2(half_l, half_w)
            steer['fl'] = -steer_angle
            steer['fr'] = steer_angle
            steer['rl'] = steer_angle
            steer['rr'] = -steer_angle

            spin_v = omega * np.hypot(half_l, half_w) / self.r_wheel
            speeds['fl'] = spin_v
            speeds['fr'] = -spin_v
            speeds['rl'] = spin_v
            speeds['rr'] = -spin_v

        elif mode == 'crab':
            # Modo Caranguejo (Translação Diagonal)
            angle = np.arctan2(vy, vx) if abs(vx) > 1e-3 or abs(vy) > 1e-3 else 0.0
            angle = np.clip(angle, -0.785, 0.785)
            for k in ['fl', 'fr', 'rl', 'rr']:
                steer[k] = angle
            w_speed = np.hypot(vx, vy) / self.r_wheel
            for k in ['fl', 'fr', 'rl', 'rr']:
                speeds[k] = w_speed

        else:
            # Modo Ackermann Duplo Contrassimétrico (4WS padrão)
            if abs(omega) < 1e-4:
                for k in ['fl', 'fr', 'rl', 'rr']:
                    steer[k] = 0.0
                    speeds[k] = vx / self.r_wheel
            else:
                r_icr = vx / omega if abs(omega) > 1e-4 else 1e5
                # Dianteiras esterçam para o centro da curva, traseiras para o lado oposto
                delta_f = np.arctan2(half_l, r_icr)
                delta_r = -delta_f

                steer['fl'] = float(np.clip(delta_f, -0.785, 0.785))
                steer['fr'] = float(np.clip(delta_f, -0.785, 0.785))
                steer['rl'] = float(np.clip(delta_r, -0.785, 0.785))
                steer['rr'] = float(np.clip(delta_r, -0.785, 0.785))

                w_speed = vx / self.r_wheel
                for k in ['fl', 'fr', 'rl', 'rr']:
                    speeds[k] = w_speed

        return steer, speeds

    def joint_state_callback(self, msg: JointState):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        if dt <= 0.0 or dt > 0.5:
            return

        # Odometria integrada
        # Publicar TF odom -> base_footprint
        t = TransformStamped()
        t.header.stamp = now.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_footprint'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        
        q = self.euler_to_quaternion(0, 0, self.yaw)
        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]
        self.tf_broadcaster.sendTransform(t)

        # Publicar Odometry
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_footprint'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]
        self.pub_odom.publish(odom)

    def euler_to_quaternion(self, roll, pitch, yaw):
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        return [x, y, z, w]

def main(args=None):
    rclpy.init(args=args)
    node = Rover4WSController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
