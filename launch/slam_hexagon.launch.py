import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('agv_ros')
    pkg_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    source_rviz_config = os.path.join(pkg_root, 'config', 'slam_hexagon.rviz')
    installed_rviz_config = os.path.join(pkg_share, 'config', 'slam_hexagon.rviz')
    rviz_config = source_rviz_config if os.path.exists(source_rviz_config) else installed_rviz_config
    params_file = os.path.join(pkg_share, 'config', 'nav2_omni_params.yaml')
    default_map_base = os.path.join(pkg_root, 'maps', 'agv_map')
    default_map_yaml = f'{default_map_base}.yaml'

    set_domain = SetEnvironmentVariable(name='ROS_DOMAIN_ID', value='69')

    gui_arg = DeclareLaunchArgument('gui', default_value='true')
    use_rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true')
    x_pose_arg = DeclareLaunchArgument('x_pose', default_value='-2.0')
    y_pose_arg = DeclareLaunchArgument('y_pose', default_value='-0.5')
    z_pose_arg = DeclareLaunchArgument('z_pose', default_value='0.06')
    yaw_arg = DeclareLaunchArgument('yaw', default_value='0.0')
    map_basename_arg = DeclareLaunchArgument(
        'map_basename',
        default_value=default_map_base,
        description='Base output path used by ros2 run nav2_map_server map_saver_cli -f <path>'
    )

    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'gazebo_display.launch.py')
        ),
        launch_arguments={
            'gui': LaunchConfiguration('gui'),
            'use_rviz': 'false',
            'x_pose': LaunchConfiguration('x_pose'),
            'y_pose': LaunchConfiguration('y_pose'),
            'z_pose': LaunchConfiguration('z_pose'),
            'yaw': LaunchConfiguration('yaw'),
        }.items()
    )

    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'slam': 'True',
            'map': default_map_yaml,
            'use_sim_time': 'True',
            'params_file': params_file,
            'autostart': 'True',
            'use_composition': 'False',
        }.items()
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_rviz'))
    )

    save_map_hint = LogInfo(
        msg=[
            'Khi quet map xong, mo terminal moi va chay: ',
            'export ROS_DOMAIN_ID=69 && ',
            'source ~/ros2_ws/install/setup.bash && ',
            'ros2 run nav2_map_server map_saver_cli -f ',
            LaunchConfiguration('map_basename'),
        ]
    )

    navigation_hint = LogInfo(
        msg=[
            'Sau khi luu map, chay navigation bang lenh: ',
            'export ROS_DOMAIN_ID=69 && ',
            'source ~/ros2_ws/install/setup.bash && ',
            'ros2 launch agv_ros navigation_hexagon.launch.py map:=',
            LaunchConfiguration('map_basename'),
            '.yaml',
        ]
    )

    return LaunchDescription([
        gui_arg,
        use_rviz_arg,
        x_pose_arg,
        y_pose_arg,
        z_pose_arg,
        yaw_arg,
        map_basename_arg,
        set_domain,
        sim_launch,
        slam_launch,
        rviz_node,
        save_map_hint,
        navigation_hint,
    ])
