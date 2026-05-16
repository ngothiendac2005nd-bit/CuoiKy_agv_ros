import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('agv_ros')
    pkg_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    source_config_dir = os.path.join(pkg_root, 'config')
    installed_config_dir = os.path.join(pkg_share, 'config')
    config_dir = source_config_dir if os.path.exists(source_config_dir) else installed_config_dir
    source_world_file = os.path.join(pkg_root, 'worlds', 'house_scan.world')
    installed_world_file = os.path.join(pkg_share, 'worlds', 'house_scan.world')
    world_file = source_world_file if os.path.exists(source_world_file) else installed_world_file
    default_map_base = os.path.join(pkg_root, 'maps', 'agv_house_map')
    source_rviz_config = os.path.join(pkg_root, 'Rviz', 'slam_view.rviz')
    installed_rviz_config = os.path.join(pkg_share, 'Rviz', 'slam_view.rviz')
    rviz_config = source_rviz_config if os.path.exists(source_rviz_config) else installed_rviz_config

    set_domain = SetEnvironmentVariable(name='ROS_DOMAIN_ID', value='69')

    gui_arg = DeclareLaunchArgument('gui', default_value='true')
    use_rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true')
    x_pose_arg = DeclareLaunchArgument('x_pose', default_value='0.0')
    y_pose_arg = DeclareLaunchArgument('y_pose', default_value='-1.0')
    z_pose_arg = DeclareLaunchArgument('z_pose', default_value='0.068')
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
            'world': world_file,
            'gui': LaunchConfiguration('gui'),
            'use_rviz': 'false',
            'use_joint_state_publisher_gui': 'false',
            'x_pose': LaunchConfiguration('x_pose'),
            'y_pose': LaunchConfiguration('y_pose'),
            'z_pose': LaunchConfiguration('z_pose'),
            'yaw': LaunchConfiguration('yaw'),
        }.items()
    )

    cartographer_node = Node(
        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
        arguments=[
            '-configuration_directory', config_dir,
            '-configuration_basename', 'cartographer_2d_house.lua',
        ],
        remappings=[('scan', '/scan')],
    )

    occupancy_grid_node = Node(
        package='cartographer_ros',
        executable='cartographer_occupancy_grid_node',
        name='cartographer_occupancy_grid_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
        arguments=['-resolution', '0.05', '-publish_period_sec', '1.0'],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('use_rviz')),
        output='screen',
    )

    delayed_sim_launch = TimerAction(
        period=1.0,
        actions=[sim_launch],
    )

    save_map_hint = LogInfo(
        msg=[
            'Khi quet xong map house, mo terminal moi va chay: ',
            'export ROS_DOMAIN_ID=69 && ',
            'source ~/ros2_ws/install/setup.bash && ',
            'ros2 run nav2_map_server map_saver_cli -f ',
            LaunchConfiguration('map_basename'),
            ' . Spawn mac dinh cua house dang la x=0.0, y=-1.0, yaw=0.0 de map luu ra dong nhat voi world.',
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
        rviz_node,
        cartographer_node,
        occupancy_grid_node,
        delayed_sim_launch,
        save_map_hint,
    ])
