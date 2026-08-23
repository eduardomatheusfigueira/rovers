from setuptools import setup
import os
from glob import glob

package_name = 'rover_gazebo_ros2'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name] if os.path.exists('resource/' + package_name) else []),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.*')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
        (os.path.join('share', package_name, 'config'), glob('config/*.*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Eduardo Matheus Figueira',
    maintainer_email='eduardo.figueira@itaipuparquetec.org.br',
    description='Controle e Simulacao Gazebo Sim do Rover Frugal 4WD/4WS via ROS 2',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'controller_4ws = rover_gazebo_ros2.controller_4ws:main',
            'teleop_keyboard = rover_gazebo_ros2.teleop_keyboard:main',
        ],
    },
)
