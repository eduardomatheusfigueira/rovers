import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('rover_gazebo_ros2')
    gz_sim_share = get_package_share_directory('ros_gz_sim')

    # Caminhos dos arquivos
    world_file = os.path.join(pkg_share, 'worlds', 'blondel_stairs.sdf')
    xacro_file = os.path.join(pkg_share, 'urdf', 'rover_frugal.urdf.xacro')
    bridge_config = os.path.join(pkg_share, 'config', 'ros_gz_bridge.yaml')

    # 1. Processar Xacro para URDF
    robot_description = Command(['xacro ', xacro_file])

    # 2. Iniciar o Gazebo Sim
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gz_sim_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_file}'}.items(),
    )

    # 3. Publicador de Estados do Robô (robot_state_publisher)
    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }]
    )

    # 4. Spawnar o Rover no Gazebo
    spawn_rover = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-string', robot_description,
            '-name', 'rover_frugal',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.40',
            '-allow_renaming', 'true'
        ]
    )

    # 5. Ponte ros_gz_bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        parameters=[{
            'config_file': bridge_config,
            'use_sim_time': True
        }]
    )

    # 6. Nó Controlador 4WS / 4WD
    controller = Node(
        package='rover_gazebo_ros2',
        executable='controller_4ws',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        gz_sim,
        robot_state_pub,
        spawn_rover,
        bridge,
        controller
    ])
