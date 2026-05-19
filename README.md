# agv_ros

ROS 2 Humble package for AGV simulation, SLAM, navigation, mecanum keyboard control, arm control, camera view, and GPS topic checking.

## 1. Required Environment

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic
- RViz2

## 2. Install Dependencies

Run these commands on a new computer before building the project:

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  ros-humble-desktop \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros2-control \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-joint-state-publisher-gui \
  ros-humble-teleop-twist-keyboard \
  ros-humble-slam-toolbox \
  ros-humble-cartographer-ros \
  ros-humble-cartographer-rviz \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-rqt-image-view \
  ros-humble-tf-transformations
```

## 3. Clone And Build

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/ngothiendac2005nd-bit/CuoiKy_agv_ros.git agv_ros

cd ~/ros2_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select agv_ros
source install/setup.bash
```

All run commands below use this same setup:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
```

If you open a new terminal, run the three setup commands above again before launching or running nodes.

## 4. Mecanum Keyboard Controller

Use this command to control the AGV by keyboard:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 run agv_ros mecanum_keyboard_teleop.py
```

## 5. SLAM And Navigation Commands

### Map 1: Simple

Run 2D Cartographer SLAM:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros cartographer_2d_mapsimple_scan.launch.py
```

Run 3D Cartographer SLAM:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros cartographer_3d_mapsimple_scan.launch.py
```

Run Navigation:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros navigation_mapsimple_scan.launch.py
```

### Map 2: House

Run 2D Cartographer SLAM:

```bash
cd ~/ros2_ws
colcon build --packages-select agv_ros
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros cartographer_2d_house.launch.py
```

Run 3D Cartographer SLAM:

```bash
cd ~/ros2_ws
colcon build --packages-select agv_ros
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros cartographer_3d_house_pointcloud.launch.py
```

Run Navigation:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros navigation_house.launch.py
```

### Map 3: Complex

Run 2D Cartographer SLAM:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros cartographer_2d_mapcomplex_scan.launch.py
```

Run 3D Cartographer SLAM:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros cartographer_3d_mapcomplex_scan.launch.py
```

Run Navigation:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros navigation_mapcomplex_scan.launch.py
```

### Hexagon Map

Run 2D Cartographer SLAM:

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros cartographer_2d.launch.py
```

Run Navigation:

```bash
cd ~/ros2_ws
colcon build --packages-select agv_ros
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros navigation_hexagon.launch.py
```

## 6. Display Robot

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 launch agv_ros display.launch.py
```

## 7. Arm Controller

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 run agv_ros arm_teleop.py
```

## 8. Camera View

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 run rqt_image_view rqt_image_view
```

## 9. GPS Data

```bash
cd ~/ros2_ws
source install/setup.bash
export ROS_DOMAIN_ID=69
ros2 topic echo /gps/data
```

## 10. Common Notes

- Build again after changing files in `launch/`, `config/`, `urdf/`, `worlds/`, or `maps/`.
- If a launch file cannot find a map, mesh, world, or RViz config, run:

```bash
cd ~/ros2_ws
colcon build --packages-select agv_ros
source install/setup.bash
```

- Do not commit generated workspace folders such as `build/`, `install/`, and `log/`.
