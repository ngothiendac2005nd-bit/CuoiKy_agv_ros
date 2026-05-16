#!/usr/bin/env python3

import math
import os
import sys
import termios
import tty

os.environ.setdefault('FASTDDS_BUILTIN_TRANSPORTS', 'UDPv4')

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


ARM_JOINT2_MIN = -1.75
ARM_JOINT2_MAX = 0.593


HELP = """
Dieu khien tay may trong Gazebo
--------------------------------
w / s : tang / giam goc Arm_joint2
a / d : tang / giam goc Arm_joint1
h     : ve vi tri home
q     : thoat
--------------------------------
"""


class ArmTeleop(Node):
    def __init__(self) -> None:
        super().__init__('arm_teleop')
        self.publisher = self.create_publisher(
            Float64MultiArray,
            '/arm_position_controller/commands',
            10,
        )
        self.joint1 = 0.0
        self.joint2 = 0.0
        self.step_joint1 = 0.12
        self.step_joint2 = 0.10

    def publish_command(self) -> None:
        msg = Float64MultiArray()
        msg.data = [self.joint1, self.joint2]
        self.publisher.publish(msg)
        self.get_logger().info(
            f'cmd -> Arm_joint1={self.joint1:.3f} rad, Arm_joint2={self.joint2:.3f} rad'
        )

    def clamp(self) -> None:
        self.joint2 = max(ARM_JOINT2_MIN, min(ARM_JOINT2_MAX, self.joint2))
        self.joint1 = math.atan2(math.sin(self.joint1), math.cos(self.joint1))


def get_key(settings) -> str:
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def main() -> None:
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init()
    node = ArmTeleop()

    print(HELP)
    node.publish_command()

    try:
        while rclpy.ok():
            key = get_key(settings)
            if key == 'q':
                break
            if key == 'a':
                node.joint1 += node.step_joint1
            elif key == 'd':
                node.joint1 -= node.step_joint1
            elif key == 'w':
                node.joint2 += node.step_joint2
            elif key == 's':
                node.joint2 -= node.step_joint2
            elif key == 'h':
                node.joint1 = 0.0
                node.joint2 = 0.0
            else:
                continue

            node.clamp()
            node.publish_command()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
