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
    workspace_src_pkg = os.path.expanduser('~/ros2_ws/src/agv_ros')
    pkg_root = workspace_src_pkg if os.path.exists(workspace_src_pkg) else os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    source_launch_dir = os.path.join(pkg_root, 'launch')
    installed_launch_dir = os.path.join(pkg_share, 'launch')
    launch_dir = source_launch_dir if os.path.exists(source_launch_dir) else installed_launch_dir
    source_config_dir = os.path.join(pkg_root, 'config')
    installed_config_dir = os.path.join(pkg_share, 'config')
    config_dir = source_config_dir if os.path.exists(source_config_dir) else installed_config_dir
    source_world_file = os.path.join(pkg_root, 'worlds', 'mapsimple_scan.world')
    installed_world_file = os.path.join(pkg_share, 'worlds', 'mapsimple_scan.world')
    world_file = source_world_file if os.path.exists(source_world_file) else installed_world_file
    source_rviz_config = os.path.join(pkg_root, 'Rviz', 'cartographer_3d_house_submaps.rviz')
    installed_rviz_config = os.path.join(pkg_share, 'Rviz', 'cartographer_3d_house_submaps.rviz')
    rviz_config = source_rviz_config if os.path.exists(source_rviz_config) else installed_rviz_config
    default_pbstream = os.path.join(pkg_root, 'maps', 'agv_mapsimple_scan_cartographer_3d.pbstream')
    default_accumulated_state = os.path.join(pkg_root, 'maps', 'agv_mapsimple_scan_cartographer_3d_accumulated.pkl')

    set_domain = SetEnvironmentVariable(name='ROS_DOMAIN_ID', value='69')

    gui_arg = DeclareLaunchArgument('gui', default_value='true')
    use_rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true')
    use_occupancy_grid_arg = DeclareLaunchArgument(
        'use_occupancy_grid',
        default_value='true',
        description='Publish a 2D occupancy grid from the 3D Cartographer trajectory',
    )
    use_accumulated_cloud_arg = DeclareLaunchArgument(
        'use_accumulated_cloud',
        default_value='true',
        description='Publish an extra PointCloud2 accumulation for RViz visualization. Cartographer submaps remain the saved map.',
    )
    load_accumulated_state_arg = DeclareLaunchArgument(
        'load_accumulated_state',
        default_value='false',
        description='Reserved for compatibility with the existing 3D launch pattern.',
    )
    x_pose_arg = DeclareLaunchArgument('x_pose', default_value='-2.5')
    y_pose_arg = DeclareLaunchArgument('y_pose', default_value='-1.5')
    z_pose_arg = DeclareLaunchArgument('z_pose', default_value='0.068')
    yaw_arg = DeclareLaunchArgument('yaw', default_value='0.0')
    pbstream_path_arg = DeclareLaunchArgument(
        'pbstream_path',
        default_value=default_pbstream,
        description='Output .pbstream path for Cartographer /write_state',
    )
    accumulated_state_path_arg = DeclareLaunchArgument(
        'accumulated_state_path',
        default_value=default_accumulated_state,
        description='Persistent state file for the accumulated RViz point cloud map',
    )

    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, 'gazebo_display_pointcloud.launch.py')),
        launch_arguments={
            'world': world_file,
            'gui': LaunchConfiguration('gui'),
            'use_rviz': 'false',
            'use_joint_state_publisher_gui': 'false',
            'x_pose': LaunchConfiguration('x_pose'),
            'y_pose': LaunchConfiguration('y_pose'),
            'z_pose': LaunchConfiguration('z_pose'),
            'yaw': LaunchConfiguration('yaw'),
        }.items(),
    )

    cartographer_node = Node(
        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
        arguments=[
            '-configuration_directory', config_dir,
            '-configuration_basename', 'cartographer_3d_house_pointcloud.lua',
        ],
        remappings=[('points2', '/points2'), ('imu', '/imu'), ('odom', '/odom')],
    )

    fake_imu_node = Node(
        package='agv_ros',
        executable='fake_imu_from_odom.py',
        name='fake_imu_from_odom',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'odom_topic': '/odom',
            'imu_topic': '/imu',
            'frame_id': 'base_link',
        }],
    )

    occupancy_grid_node = Node(
        package='cartographer_ros',
        executable='cartographer_occupancy_grid_node',
        name='cartographer_occupancy_grid_node',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_occupancy_grid')),
        parameters=[{'use_sim_time': True}],
        arguments=['-resolution', '0.05', '-publish_period_sec', '1.0'],
    )

    accumulated_cloud_node = Node(
        package='agv_ros',
        executable='accumulate_pointcloud_map.py',
        name='accumulate_pointcloud_map',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_accumulated_cloud')),
        parameters=[{
            'use_sim_time': True,
            'input_topic': '/points2',
            'fallback_input_topic': '',
            'output_topic': '/accumulated_points2',
            'fixed_frame': 'odom',
            'voxel_size': 0.05,
            'min_z': -0.2,
            'max_z': 2.5,
            'publish_period': 0.5,
            'transform_timeout': 0.2,
            'fallback_to_latest_transform': False,
            'max_published_points': 250000,
            'status_period': 3.0,
            'state_file': LaunchConfiguration('accumulated_state_path'),
            'load_existing': False,
            'autosave_period': 0.0,
            'use_motion_filter': False,
            'min_translation': 0.02,
            'min_rotation': 0.02,
        }],
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

    save_map_hint = LogInfo(
        msg=[
            '3D simple mapping: luu pbstream bang lenh ',
            'export ROS_DOMAIN_ID=69 && source ~/ros2_ws/install/setup.bash && ',
            'ros2 service call /write_state cartographer_ros_msgs/srv/WriteState ',
            '"{filename: \'',
            LaunchConfiguration('pbstream_path'),
            '\', include_unfinished_submaps: true}"',
            '. State cloud RViz duoc luu tai ',
            LaunchConfiguration('accumulated_state_path'),
            '.',
        ]
    )

    return LaunchDescription([
        gui_arg,
        use_rviz_arg,
        use_occupancy_grid_arg,
        use_accumulated_cloud_arg,
        load_accumulated_state_arg,
        x_pose_arg,
        y_pose_arg,
        z_pose_arg,
        yaw_arg,
        pbstream_path_arg,
        accumulated_state_path_arg,
        set_domain,
        rviz_node,
        fake_imu_node,
        cartographer_node,
        occupancy_grid_node,
        accumulated_cloud_node,
        TimerAction(period=1.0, actions=[sim_launch]),
        save_map_hint,
    ])
