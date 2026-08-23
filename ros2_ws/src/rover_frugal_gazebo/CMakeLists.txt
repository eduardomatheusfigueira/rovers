cmake_minimum_required(VERSION 3.8)
project(rover_frugal_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY worlds launch config DESTINATION share/${PROJECT_NAME})

# O gz-sim precisa encontrar as malhas referenciadas como package://
ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")

ament_package()
