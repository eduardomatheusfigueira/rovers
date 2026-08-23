"""Sobe os controladores do ros2_control e os três nós de controle do rover.

    ros2 launch rover_frugal_control controle.launch.py
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def spawner(nome: str) -> Node:
    return Node(package="controller_manager", executable="spawner",
                arguments=[nome, "--controller-manager", "/controller_manager"],
                output="screen")


def generate_launch_description() -> LaunchDescription:
    cfg = PathJoinSubstitution([
        FindPackageShare("rover_frugal_control"), "config", "controladores.yaml"])
    tempo_sim = LaunchConfiguration("use_sim_time")

    broadcaster = spawner("joint_state_broadcaster")
    esterco = spawner("esterco_controller")
    tracao = spawner("tracao_controller")
    passivas = spawner("passivas_controller")

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),

        broadcaster,
        # Os controladores só entram depois do broadcaster: sem estado de junta
        # publicado, o nó de molas passivas comandaria esforço às cegas.
        RegisterEventHandler(OnProcessExit(target_action=broadcaster,
                                           on_exit=[esterco, tracao, passivas])),

        Node(package="rover_frugal_control", executable="cinematica_4ws",
             name="cinematica_4ws", parameters=[cfg, {"use_sim_time": tempo_sim}],
             output="screen"),
        Node(package="rover_frugal_control", executable="molas_passivas",
             name="molas_passivas", parameters=[cfg, {"use_sim_time": tempo_sim}],
             output="screen"),
        Node(package="rover_frugal_control", executable="supervisor",
             name="supervisor", parameters=[cfg, {"use_sim_time": tempo_sim}],
             output="screen"),
    ])
