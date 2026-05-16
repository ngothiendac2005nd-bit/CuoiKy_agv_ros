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
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # House map đã được lưu với một độ lệch cố định giữa world của Gazebo
    # và map của AMCL. Giữ nguyên độ lệch hiệu chỉnh cũ khi đổi vị trí spawn
    # để scan khớp với map tĩnh ngay từ đầu.
    house_spawn_x = -4.5
    house_spawn_y = -3.8
    house_spawn_yaw = 0.0
    map_offset_x = -0.16
    map_offset_y = 1.46
    map_offset_yaw = 0.315

    source_rviz_config = os.path.join(pkg_root, 'config', 'navigation_house.rviz')
    installed_rviz_config = os.path.join(pkg_share, 'config', 'navigation_house.rviz')
    rviz_config = source_rviz_config if os.path.exists(source_rviz_config) else installed_rviz_config
    source_params_file = os.path.join(pkg_root, 'config', 'nav2_house_params.yaml')
    installed_params_file = os.path.join(pkg_share, 'config', 'nav2_house_params.yaml')
    params_file = source_params_file if os.path.exists(source_params_file) else installed_params_file
    default_map = os.path.join(pkg_root, 'maps', 'agv_house_map.yaml')
    source_world_file = os.path.join(pkg_root, 'worlds', 'house_scan.world')
    installed_world_file = os.path.join(pkg_share, 'worlds', 'house_scan.world')
    world_file = source_world_file if os.path.exists(source_world_file) else installed_world_file

    set_domain = SetEnvironmentVariable(name='ROS_DOMAIN_ID', value='69')

    gui_arg = DeclareLaunchArgument('gui', default_value='true')
    use_rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true')
    x_pose_arg = DeclareLaunchArgument('x_pose', default_value=str(house_spawn_x))
    y_pose_arg = DeclareLaunchArgument('y_pose', default_value=str(house_spawn_y))
    z_pose_arg = DeclareLaunchArgument('z_pose', default_value='0.068')
    yaw_arg = DeclareLaunchArgument('yaw', default_value=str(house_spawn_yaw))
    initial_pose_x_arg = DeclareLaunchArgument(
        'initial_pose_x',
        default_value=f'{house_spawn_x + map_offset_x:.3f}'
    )
    initial_pose_y_arg = DeclareLaunchArgument(
        'initial_pose_y',
        default_value=f'{house_spawn_y + map_offset_y:.3f}'
    )
    initial_pose_yaw_arg = DeclareLaunchArgument(
        'initial_pose_yaw',
        default_value=f'{house_spawn_yaw + map_offset_yaw:.3f}'
    )
    map_arg = DeclareLaunchArgument(
        'map',
        default_value=default_map,
        description='Absolute path to the saved house map yaml file'
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

    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'slam': 'False',
            'map': LaunchConfiguration('map'),
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
        parameters=[{'use_sim_time': True}],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_rviz'))
    )

    initial_pose_node = Node(
        package='agv_ros',
        executable='publish_initial_pose.py',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'x': LaunchConfiguration('initial_pose_x'),
            'y': LaunchConfiguration('initial_pose_y'),
            'yaw': LaunchConfiguration('initial_pose_yaw'),
            'delay_sec': 1.0,
            'repeat_count': 5,
        }],
    )

    delayed_nav_launch = TimerAction(
        period=3.0,
        actions=[nav_launch],
    )

    delayed_initial_pose = TimerAction(
        period=7.0,
        actions=[initial_pose_node],
    )

    initial_pose_hint = LogInfo(
        msg='House nav sẽ tự publish initial pose mặc định ở góc trái dưới của map house sau khi Nav2 lên. Nếu cần, hãy đặt lại 2D Pose Estimate và tinh chỉnh x_pose/y_pose/yaw cùng initial_pose_x/y/yaw cho khớp.'
    )

    return LaunchDescription([
        gui_arg,
        use_rviz_arg,
        x_pose_arg,
        y_pose_arg,
        z_pose_arg,
        yaw_arg,
        initial_pose_x_arg,
        initial_pose_y_arg,
        initial_pose_yaw_arg,
        map_arg,
        set_domain,
        rviz_node,
        sim_launch,
        delayed_nav_launch,
        delayed_initial_pose,
        initial_pose_hint,
    ])
