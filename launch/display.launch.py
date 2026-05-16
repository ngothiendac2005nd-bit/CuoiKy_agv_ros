import os
import re

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('agv_ros')
    urdf_file = os.path.join(pkg_share, 'urdf', 'demo2.urdf')

    with open(urdf_file, 'r') as infp:
        robot_description = infp.read()
    robot_description = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', robot_description, count=1)
    robot_description = re.sub(r'<!--.*?-->\s*', '', robot_description, flags=re.DOTALL)

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}]
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui'
        ),
        Node(
            package='rviz2',
            executable='rviz2'
        )
    ])
