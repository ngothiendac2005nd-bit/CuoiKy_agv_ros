import os
import re

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, LogInfo, RegisterEventHandler, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def _make_pointcloud_robot_description(robot_desc: str) -> str:
    """Keep the source URDF unchanged and make the Gazebo lidar a 3D cloud."""
    robot_desc = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', robot_desc, count=1)
    robot_desc = re.sub(r'<!--.*?-->\s*', '', robot_desc, flags=re.DOTALL)

    robot_desc = robot_desc.replace(
        """          <horizontal>
            <samples>360</samples>
            <resolution>1</resolution>
            <min_angle>-3.14159</min_angle>
            <max_angle>3.14159</max_angle>
          </horizontal>""",
        """          <horizontal>
            <samples>720</samples>
            <resolution>1</resolution>
            <min_angle>-3.14159</min_angle>
            <max_angle>3.14159</max_angle>
          </horizontal>
          <vertical>
            <samples>32</samples>
            <resolution>1</resolution>
            <min_angle>-0.40</min_angle>
            <max_angle>0.55</max_angle>
          </vertical>""",
        1,
    )
    robot_desc = robot_desc.replace('<update_rate>10</update_rate>', '<update_rate>8</update_rate>', 1)
    robot_desc = robot_desc.replace('<max>12.0</max>', '<max>5.0</max>', 1)
    robot_desc = robot_desc.replace('<remapping>~/out:=scan</remapping>', '<remapping>~/out:=points2</remapping>', 1)
    robot_desc = robot_desc.replace('<output_type>sensor_msgs/LaserScan</output_type>', '<output_type>sensor_msgs/PointCloud2</output_type>', 1)
    return robot_desc


def generate_launch_description():
    package_name = 'agv_ros'
    pkg_share = get_package_share_directory(package_name)
    workspace_src_pkg = os.path.expanduser('~/ros2_ws/src/agv_ros')
    pkg_root = workspace_src_pkg if os.path.exists(workspace_src_pkg) else os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    gazebo_pkg_dir = get_package_share_directory('gazebo_ros')
    turtlebot3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    turtlebot3_model_dir = os.path.join(turtlebot3_gazebo_dir, 'models')
    default_world = os.path.join(turtlebot3_gazebo_dir, 'worlds', 'turtlebot3_world.world')

    source_controller_file = os.path.join(pkg_root, 'config', 'arm_controllers.yaml')
    installed_controller_file = os.path.join(pkg_share, 'config', 'arm_controllers.yaml')
    controller_file = source_controller_file if os.path.exists(source_controller_file) else installed_controller_file
    source_urdf_file = os.path.join(pkg_root, 'urdf', 'demo2.urdf')
    installed_urdf_file = os.path.join(pkg_share, 'urdf', 'demo2.urdf')
    urdf_file = source_urdf_file if os.path.exists(source_urdf_file) else installed_urdf_file
    source_rviz_file = os.path.join(pkg_root, 'Rviz', 'view.rviz')
    installed_rviz_file = os.path.join(pkg_share, 'Rviz', 'view.rviz')
    rviz_file = source_rviz_file if os.path.exists(source_rviz_file) else installed_rviz_file
    joint_state_gui_bridge_script = os.path.join(pkg_root, 'scripts', 'joint_state_gui_bridge.py')

    with open(urdf_file, 'r') as infp:
        robot_desc = _make_pointcloud_robot_description(infp.read())
    robot_desc = robot_desc.replace('__ARM_CONTROLLER_CONFIG__', controller_file)

    world_arg = DeclareLaunchArgument('world', default_value=default_world, description='Gazebo world file')
    gui_arg = DeclareLaunchArgument('gui', default_value='true', description='Set false to run Gazebo without gzclient')
    x_pose_arg = DeclareLaunchArgument('x_pose', default_value='0.0', description='Initial robot x position')
    y_pose_arg = DeclareLaunchArgument('y_pose', default_value='-1.0', description='Initial robot y position')
    z_pose_arg = DeclareLaunchArgument('z_pose', default_value='0.068', description='Initial robot z position')
    yaw_arg = DeclareLaunchArgument('yaw', default_value='0.0', description='Initial robot yaw angle in radians')
    use_rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true', description='Launch RViz2')
    use_joint_state_publisher_gui_arg = DeclareLaunchArgument(
        'use_joint_state_publisher_gui',
        default_value='true',
        description='Launch joint_state_publisher_gui and bridge sliders to Gazebo controllers',
    )

    set_gazebo_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=[os.path.dirname(pkg_share), os.pathsep, turtlebot3_model_dir, os.pathsep, EnvironmentVariable('GAZEBO_MODEL_PATH', default_value='')],
    )
    disable_fastdds_shm = SetEnvironmentVariable(name='FASTDDS_BUILTIN_TRANSPORTS', value='UDPv4')
    set_ros_domain_id = SetEnvironmentVariable(name='ROS_DOMAIN_ID', value='69')

    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': True}],
    )

    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        output='screen',
        parameters=[{'use_sim_time': True}],
        remappings=[('joint_states', 'joint_states_gui')],
        condition=IfCondition(LaunchConfiguration('use_joint_state_publisher_gui')),
    )

    joint_state_gui_bridge_node = ExecuteProcess(
        cmd=['python3', joint_state_gui_bridge_script],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_joint_state_publisher_gui')),
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_pkg_dir, 'launch', 'gazebo.launch.py')),
        launch_arguments={'world': LaunchConfiguration('world'), 'gui': LaunchConfiguration('gui')}.items(),
    )

    spawn_node = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'agv_ros_pointcloud',
            '-timeout', '60.0',
            '-x', LaunchConfiguration('x_pose'),
            '-y', LaunchConfiguration('y_pose'),
            '-z', LaunchConfiguration('z_pose'),
            '-Y', LaunchConfiguration('yaw'),
        ],
        output='screen',
    )

    joint_state_broadcaster_spawner = Node(package='controller_manager', executable='spawner', arguments=['joint_state_broadcaster'], output='screen')
    wheel_velocity_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['wheel_velocity_controller', '--param-file', controller_file],
        output='screen',
    )
    arm_position_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_position_controller', '--param-file', controller_file],
        output='screen',
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_file],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_rviz')),
    )

    teleop_hint = LogInfo(
        msg=(
            'Keyboard teleop: export ROS_DOMAIN_ID=69 && source ~/ros2_ws/install/setup.bash && '
            'ros2 run agv_ros mecanum_keyboard_teleop.py'
        )
    )

    return LaunchDescription([
        world_arg,
        gui_arg,
        x_pose_arg,
        y_pose_arg,
        z_pose_arg,
        yaw_arg,
        use_rviz_arg,
        use_joint_state_publisher_gui_arg,
        disable_fastdds_shm,
        set_ros_domain_id,
        set_gazebo_model_path,
        rsp_node,
        joint_state_publisher_gui_node,
        joint_state_gui_bridge_node,
        gazebo,
        spawn_node,
        RegisterEventHandler(OnProcessExit(target_action=spawn_node, on_exit=[joint_state_broadcaster_spawner])),
        RegisterEventHandler(OnProcessExit(target_action=joint_state_broadcaster_spawner, on_exit=[wheel_velocity_controller_spawner])),
        RegisterEventHandler(OnProcessExit(target_action=wheel_velocity_controller_spawner, on_exit=[arm_position_controller_spawner])),
        teleop_hint,
        rviz_node,
    ])
