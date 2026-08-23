"""
Sobe o Gazebo com o percurso do Parquetec, gera o rover e liga a ponte ROS.

    ros2 launch rover_frugal_gazebo simulacao.launch.py
    ros2 launch rover_frugal_gazebo simulacao.launch.py mundo:=bancada_degrau.sdf aro_elastico:=false
    ros2 launch rover_frugal_gazebo simulacao.launch.py mundo:=escada_molhada.sdf

Escolha da variante de roda (ver 03_Simulacao/05 §4.3):
  aro_elastico:=true   superfície contínua de rolamento — percurso e piso plano
  aro_elastico:=false  raios expostos — marcha em escada
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (Command, LaunchConfiguration,
                                  PathJoinSubstitution, TextSubstitution)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg_desc = FindPackageShare("rover_frugal_description")
    pkg_gz = FindPackageShare("rover_frugal_gazebo")
    pkg_ctrl = FindPackageShare("rover_frugal_control")

    mundo = LaunchConfiguration("mundo")
    aro = LaunchConfiguration("aro_elastico")
    x0 = LaunchConfiguration("x")
    z0 = LaunchConfiguration("z")

    descricao = Command([
        "xacro ", PathJoinSubstitution([pkg_desc, "urdf", "rover_frugal.urdf.xacro"]),
        " aro_elastico:=", aro,
        " usar_ros2_control:=true",
        " controladores:=", PathJoinSubstitution([pkg_ctrl, "config", "controladores.yaml"]),
    ])

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])]),
        launch_arguments={
            "gz_args": [PathJoinSubstitution([pkg_gz, "worlds", mundo]),
                        TextSubstitution(text=" -r -v 3")],
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument("mundo", default_value="percurso_parquetec.sdf"),
        DeclareLaunchArgument("aro_elastico", default_value="true"),
        DeclareLaunchArgument("x", default_value="0.0"),
        DeclareLaunchArgument("z", default_value="0.30"),

        gz,

        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": descricao, "use_sim_time": True}],
             output="screen"),

        Node(package="ros_gz_sim", executable="create", output="screen",
             arguments=["-topic", "/robot_description", "-name", "rover_frugal",
                        "-x", x0, "-y", "0.0", "-z", z0]),

        Node(package="ros_gz_bridge", executable="parameter_bridge", output="screen",
             parameters=[{"config_file": PathJoinSubstitution(
                 [pkg_gz, "config", "ponte.yaml"]), "use_sim_time": True}]),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([pkg_ctrl, "launch", "controle.launch.py"])]),
            launch_arguments={"use_sim_time": "true"}.items(),
        ),
    ])
