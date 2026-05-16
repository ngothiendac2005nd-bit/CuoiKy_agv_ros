# agv_ros

ROS 2 Humble package for an AGV simulation with Gazebo, RViz, Cartographer, SLAM Toolbox, and Nav2 launch files.

## Environment

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic

## Install Dependencies

```bash
sudo apt update
sudo apt install -y \
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
  ros-humble-tf-transformations \
  python3-colcon-common-extensions
```

## Build

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone <YOUR_GITHUB_REPO_URL> agv_ros
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select agv_ros
source install/setup.bash
```

## Run Examples

Display the robot in RViz:

```bash
ros2 launch agv_ros display.launch.py
```

Run Gazebo with the simple scan world:

```bash
ros2 launch agv_ros gazebo_display.launch.py
```

Run Cartographer 2D with the simple scan world:

```bash
ros2 launch agv_ros cartographer_2d_mapsimple_scan.launch.py
```

Run navigation with the simple scan map:

```bash
ros2 launch agv_ros navigation_mapsimple_scan.launch.py
```

Other launch files are available in `launch/`.

## Notes

- If a launch file cannot find a map, world, mesh, or RViz config, rebuild and source the workspace again:

```bash
cd ~/ros2_ws
colcon build --packages-select agv_ros
source install/setup.bash
```

- Keep generated workspace folders such as `build/`, `install/`, and `log/` out of Git.

