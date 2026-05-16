#!/usr/bin/env python3

import math
import os
from typing import Dict

os.environ.setdefault('FASTDDS_BUILTIN_TRANSPORTS', 'UDPv4')
os.environ.setdefault('ROS_DOMAIN_ID', '69')

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray


ARM_JOINTS = ('Arm_joint1', 'Arm_joint2')
WHEEL_JOINTS = (
    'Frontleft_joint',
    'FrontRight_joint',
    'BackLeft_joint',
    'BackRight_joint',
)
ARM_JOINT2_MIN = -1.75
ARM_JOINT2_MAX = 0.593


class JointStateGuiBridge(Node):
    def __init__(self) -> None:
        super().__init__('joint_state_gui_bridge')

        self.declare_parameter('wheel_gain', 6.0)
        self.declare_parameter('max_wheel_velocity', 8.0)
        self.declare_parameter('wheel_deadband', 0.02)
        self.declare_parameter('publish_rate', 20.0)

        self.wheel_gain = float(self.get_parameter('wheel_gain').value)
        self.max_wheel_velocity = float(self.get_parameter('max_wheel_velocity').value)
        self.wheel_deadband = float(self.get_parameter('wheel_deadband').value)
        publish_rate = float(self.get_parameter('publish_rate').value)

        self.gui_targets: Dict[str, float] = {}
        self.last_arm_command: list[float] | None = None
        self.last_wheel_command: list[float] | None = None

        self.arm_publisher = self.create_publisher(
            Float64MultiArray,
            '/arm_position_controller/commands',
            10,
        )
        self.wheel_publisher = self.create_publisher(
            Float64MultiArray,
            '/wheel_velocity_controller/commands',
            10,
        )

        self.create_subscription(JointState, '/joint_states_gui', self.gui_callback, 10)
        self.create_timer(1.0 / publish_rate, self.publish_commands)

        self.get_logger().info('Joint-state GUI bridge ready')

    def gui_callback(self, msg: JointState) -> None:
        for name, position in zip(msg.name, msg.position):
            self.gui_targets[name] = position

    def publish_commands(self) -> None:
        self.publish_arm_command()
        self.publish_wheel_command()

    def publish_arm_command(self) -> None:
        if not all(joint in self.gui_targets for joint in ARM_JOINTS):
            return

        joint1 = math.atan2(
            math.sin(self.gui_targets['Arm_joint1']),
            math.cos(self.gui_targets['Arm_joint1']),
        )
        joint2 = max(ARM_JOINT2_MIN, min(ARM_JOINT2_MAX, self.gui_targets['Arm_joint2']))
        command = [joint1, joint2]

        if self.last_arm_command == command:
            return

        msg = Float64MultiArray()
        msg.data = command
        self.arm_publisher.publish(msg)
        self.last_arm_command = command

    def publish_wheel_command(self) -> None:
        if not all(joint in self.gui_targets for joint in WHEEL_JOINTS):
            return

        command = []
        for joint in WHEEL_JOINTS:
            velocity = self.wheel_gain * self.gui_targets[joint]
            if abs(velocity) < self.wheel_deadband:
                velocity = 0.0
            velocity = max(-self.max_wheel_velocity, min(self.max_wheel_velocity, velocity))
            command.append(velocity)

        if self.last_wheel_command == command:
            return

        msg = Float64MultiArray()
        msg.data = command
        self.wheel_publisher.publish(msg)
        self.last_wheel_command = command


def main() -> None:
    rclpy.init()
    node = JointStateGuiBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
