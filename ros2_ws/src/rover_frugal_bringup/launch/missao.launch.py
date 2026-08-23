"""
Missão completa: Gazebo + rover + controle + teleoperação + telemetria.

    ros2 launch rover_frugal_bringup missao.launch.py

Em outro terminal, para pilotar:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard
Trocar de modo cinemático (o rover PARA para reorientar as rodas — δs = 2):
    ros2 topic pub --once /cinematica_4ws/modo std_msgs/String "data: crab"
Liberar o modo escada (exige confirmação de piso seco — μ ≥ 0,72):
    ros2 topic pub --once /supervisor/piso_seco std_msgs/Bool "data: true"
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg_gz = FindPackageShare("rover_frugal_gazebo")

    return LaunchDescription([
        DeclareLaunchArgument("mundo", default_value="percurso_parquetec.sdf"),
        DeclareLaunchArgument("aro_elastico", default_value="true"),
        DeclareLaunchArgument("telemetria", default_value="true"),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([pkg_gz, "launch", "simulacao.launch.py"])]),
            launch_arguments={
                "mundo": LaunchConfiguration("mundo"),
                "aro_elastico": LaunchConfiguration("aro_elastico"),
            }.items(),
        ),

        Node(package="rover_frugal_bringup", executable="registrador",
             name="registrador_telemetria", output="screen",
             parameters=[{"use_sim_time": True}]),
    ])
