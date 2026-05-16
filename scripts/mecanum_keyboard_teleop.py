#!/usr/bin/env python3

import os
import select
import sys
import termios
import tty

os.environ.setdefault('FASTDDS_BUILTIN_TRANSPORTS', 'UDPv4')
os.environ.setdefault('ROS_DOMAIN_ID', '69')

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


HELP = """
Dieu khien AGV bang planar_move trong Gazebo
-----------------------------------
u  i  o   : cheo trai / tien / cheo phai
j  k  l   : trai / dung / phai
m  ,  .   : cheo lui trai / lui / cheo lui phai
a / d     : xoay trai / xoay phai
+ / -     : tang / giam toc do
r         : reset toc do mac dinh
q         : thoat
-----------------------------------
Lenh chuyen dong se duoc giu cho toi khi bam k hoac phim space de dung.
"""


class MecanumKeyboardTeleop(Node):
    def __init__(self) -> None:
        super().__init__('mecanum_keyboard_teleop')
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)

        self.declare_parameter('linear_speed', 0.28)
        self.declare_parameter('angular_speed', 3.5)
        self.declare_parameter('speed_step', 0.05)
        self.declare_parameter('turn_step', 0.1)
        self.declare_parameter('publish_rate', 20.0)

        self.default_linear_speed = float(self.get_parameter('linear_speed').value)
        self.default_angular_speed = float(self.get_parameter('angular_speed').value)
        self.speed_step = float(self.get_parameter('speed_step').value)
        self.publish_rate = float(self.get_parameter('publish_rate').value)

        self.linear_speed = self.default_linear_speed
        self.angular_speed = self.default_angular_speed
        self.current_motion = (0.0, 0.0, 0.0)
        self.last_sent_motion = None

        self.motion_bindings = {
            'u': (1.0, 1.0, 0.0),
            'i': (1.0, 0.0, 0.0),
            'o': (1.0, -1.0, 0.0),
            'j': (0.0, 1.0, 0.0),
            'k': (0.0, 0.0, 0.0),
            'l': (0.0, -1.0, 0.0),
            'm': (-1.0, 1.0, 0.0),
            ',': (-1.0, 0.0, 0.0),
            '.': (-1.0, -1.0, 0.0),
            'a': (0.0, 0.0, 1.0),
            'd': (0.0, 0.0, -1.0),
            'q': (0.0, 0.0, 1.0),
            'e': (0.0, 0.0, -1.0),
            'A': (0.0, 0.0, 1.0),
            'D': (0.0, 0.0, -1.0),
        }
        self.create_timer(1.0 / self.publish_rate, self.publish_current_motion)

    def publish_twist(self, x: float, y: float, yaw: float) -> None:
        msg = Twist()
        msg.linear.x = x * self.linear_speed
        msg.linear.y = y * self.linear_speed
        msg.angular.z = yaw * self.angular_speed
        self.publisher.publish(msg)
        motion = (x, y, yaw)
        if motion != self.last_sent_motion:
            self.get_logger().info(
                f'cmd_vel x={msg.linear.x:.2f}, y={msg.linear.y:.2f}, wz={msg.angular.z:.2f}'
            )
            self.last_sent_motion = motion

    def publish_current_motion(self) -> None:
        x, y, yaw = self.current_motion
        self.publish_twist(x, y, yaw)

    def stop(self) -> None:
        self.current_motion = (0.0, 0.0, 0.0)
        self.publish_current_motion()

    def change_speed(self, delta: float) -> None:
        self.linear_speed = max(0.05, self.linear_speed + delta)
        self.angular_speed = max(0.2, self.angular_speed + (delta * 2.0))
        self.print_speed()
        self.publish_current_motion()

    def reset_speed(self) -> None:
        self.linear_speed = self.default_linear_speed
        self.angular_speed = self.default_angular_speed
        self.print_speed()
        self.publish_current_motion()

    def print_speed(self) -> None:
        self.get_logger().info(
            f'linear={self.linear_speed:.2f} m/s, angular={self.angular_speed:.2f} rad/s'
        )


def get_key(settings) -> str:
    tty.setraw(sys.stdin.fileno())
    ready, _, _ = select.select([sys.stdin], [], [], 0.1)
    key = sys.stdin.read(1) if ready else ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def main() -> None:
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init()
    node = MecanumKeyboardTeleop()

    print(HELP)
    node.print_speed()
    node.stop()

    try:
        while rclpy.ok():
            key = get_key(settings)
            if key == 'q':
                break
            if key in node.motion_bindings:
                node.current_motion = node.motion_bindings[key]
                node.publish_current_motion()
                continue
            if key in (' ', 'k'):
                node.stop()
                continue
            if key == '+':
                node.change_speed(node.speed_step)
                continue
            if key == '-':
                node.change_speed(-node.speed_step)
                continue
            if key == 'r':
                node.reset_speed()
                continue
    finally:
        node.stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
