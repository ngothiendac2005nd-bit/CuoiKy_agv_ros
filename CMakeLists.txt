cmake_minimum_required(VERSION 3.5)
project(agv_ros)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

find_package(ament_cmake REQUIRED)

ament_environment_hooks(
  "${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/fastdds_udp.sh.in"
)

# Install các thư mục chứa dữ liệu mô hình vào workspace
install(
  DIRECTORY config launch maps meshes Rviz urdf worlds
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/arm_teleop.py
    scripts/accumulate_pointcloud_map.py
    scripts/export_accumulated_map.py
    scripts/fake_imu_from_odom.py
    scripts/joint_state_gui_bridge.py
    scripts/mecanum_keyboard_teleop.py
    scripts/mecanum_drive_controller.py
    scripts/odom_to_tf_broadcaster.py
    scripts/publish_initial_pose.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
