"""Abre o rover no RViz2 com sliders de junta — útil para conferir a geometria.

    ros2 launch rover_frugal_description visualizar.launch.py
    ros2 launch rover_frugal_description visualizar.launch.py aro_elastico:=false
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg = FindPackageShare("rover_frugal_description")
    aro = LaunchConfiguration("aro_elastico")
    gui = LaunchConfiguration("gui")

    descricao = Command([
        "xacro ", PathJoinSubstitution([pkg, "urdf", "rover_frugal.urdf.xacro"]),
        " aro_elastico:=", aro, " usar_ros2_control:=false",
    ])

    return LaunchDescription([
        DeclareLaunchArgument("aro_elastico", default_value="true",
                              description="true: roda com aro (rolamento contínuo); "
                                          "false: raios expostos (marcha em escada)"),
        DeclareLaunchArgument("gui", default_value="true"),

        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": descricao}], output="screen"),

        Node(package="joint_state_publisher_gui", executable="joint_state_publisher_gui",
             condition=IfCondition(gui)),

        Node(package="rviz2", executable="rviz2", output="screen",
             arguments=["-d", PathJoinSubstitution([pkg, "rviz", "rover.rviz"])]),
    ])
