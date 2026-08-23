"""
Ensaio ENS-06 em simulação: subida instrumentada de um lance de escada.

Roda sem interface gráfica, com piloto automático determinístico, e grava a
telemetria no mesmo formato do gêmeo digital 3D e do firmware. É a corrida que
alimenta a validação do modelo (03_Simulacao/04, §4.3).

    ros2 launch rover_frugal_bringup ensaio_escada.launch.py arquivo:=/tmp/ens06.csv

A variante da roda é `aro_elastico:=false` por padrão: na escada quem trabalha
são os raios, e é o contato deles que o ensaio precisa observar.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg_gz = FindPackageShare("rover_frugal_gazebo")

    return LaunchDescription([
        DeclareLaunchArgument("mundo", default_value="bancada_degrau.sdf"),
        DeclareLaunchArgument("aro_elastico", default_value="false"),
        DeclareLaunchArgument("arquivo", default_value="/tmp/ensaio_escada.csv"),
        DeclareLaunchArgument("velocidade_escada", default_value="0.25"),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([pkg_gz, "launch", "simulacao.launch.py"])]),
            launch_arguments={
                "mundo": LaunchConfiguration("mundo"),
                "aro_elastico": LaunchConfiguration("aro_elastico"),
                "x": "0.0",
            }.items(),
        ),

        Node(package="rover_frugal_bringup", executable="registrador",
             name="registrador_telemetria", output="screen",
             parameters=[{"arquivo": LaunchConfiguration("arquivo"),
                          "use_sim_time": True}]),

        # O piloto entra depois que os controladores assentaram: comandar tração
        # antes de o controlador de esforço estar ativo faria a suspensão colapsar.
        TimerAction(period=8.0, actions=[
            Node(package="rover_frugal_bringup", executable="piloto_ensaio",
                 name="piloto_ensaio", output="screen",
                 parameters=[{"modo": "stair",
                              "velocidade_escada": LaunchConfiguration("velocidade_escada"),
                              "use_sim_time": True}]),
        ]),
    ])
