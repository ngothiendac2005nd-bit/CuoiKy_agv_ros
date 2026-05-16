#!/usr/bin/env python3

import os
from typing import List

os.environ.setdefault('FASTDDS_BUILTIN_TRANSPORTS', 'UDPv4')
os.environ.setdefault('ROS_DOMAIN_ID', '69')

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


class MecanumDriveController(Node):
    def __init__(self) -> None:
        super().__init__('mecanum_drive_controller')

        self.declare_parameter('wheel_radius', 0.05)
        self.declare_parameter('wheel_base', 0.0921)
        self.declare_parameter('track_width', 0.1593)
        self.declare_parameter('max_wheel_speed', 15.0)
        self.declare_parameter('wheel_signs', [1.0, 1.0, 1.0, 1.0])
        self.declare_parameter('cmd_timeout', 3600.0)
        self.declare_parameter('control_rate', 30.0)

        self.wheel_radius = float(self.get_parameter('wheel_radius').value)
        self.wheel_base = float(self.get_parameter('wheel_base').value)
        self.track_width = float(self.get_parameter('track_width').value)
        self.max_wheel_speed = float(self.get_parameter('max_wheel_speed').value)
        self.wheel_signs = [float(v) for v in self.get_parameter('wheel_signs').value]
        self.cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self.control_rate = float(self.get_parameter('control_rate').value)
        self.kinematic_radius = (self.wheel_base / 2.0) + (self.track_width / 2.0)
        self.last_cmd = Twist()
        self.last_cmd_time = self.get_clock().now()
        self.last_logged_wheel_commands: List[float] | None = None

        self.command_publisher = self.create_publisher(
            Float64MultiArray,
            '/wheel_velocity_controller/commands',
            10,
        )
        self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.create_timer(1.0 / self.control_rate, self.control_loop)

        self.get_logger().info(
            'Mecanum controller ready: '
            f'wheel_signs={self.wheel_signs}, '
            'order=[front_left, front_right, back_left, back_right]'
        )

    def cmd_vel_callback(self, msg: Twist) -> None:
        self.last_cmd = msg
        self.last_cmd_time = self.get_clock().now()
        self.get_logger().info(
            f'recv cmd_vel x={msg.linear.x:.2f}, y={msg.linear.y:.2f}, wz={msg.angular.z:.2f}'
        )
    
    def control_loop(self) -> None:
        cmd = Twist() if self.command_is_stale() else self.last_cmd
        self.publish_wheel_commands(cmd)

    def publish_wheel_commands(self, cmd: Twist) -> None:
        vx = cmd.linear.x
        vy = cmd.linear.y
        wz = cmd.angular.z

        raw_wheels = [
            (vx - vy - self.kinematic_radius * wz) / self.wheel_radius,
            (vx + vy + self.kinematic_radius * wz) / self.wheel_radius,
            (vx + vy - self.kinematic_radius * wz) / self.wheel_radius,
            (vx - vy + self.kinematic_radius * wz) / self.wheel_radius,
        ]

        wheel_commands = self.apply_signs_and_limits(raw_wheels)

        command_msg = Float64MultiArray()
        command_msg.data = wheel_commands
        self.command_publisher.publish(command_msg)
        if self.should_log_wheel_commands(wheel_commands):
            self.get_logger().info(
                'wheel cmd '
                f'[{wheel_commands[0]:.2f}, {wheel_commands[1]:.2f}, '
                f'{wheel_commands[2]:.2f}, {wheel_commands[3]:.2f}]'
            )
            self.last_logged_wheel_commands = wheel_commands.copy()

    def command_is_stale(self) -> bool:
        age = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9
        return age > self.cmd_timeout

    def apply_signs_and_limits(self, wheel_commands: List[float]) -> List[float]:
        signed = [cmd * sign for cmd, sign in zip(wheel_commands, self.wheel_signs)]
        max_abs = max(abs(cmd) for cmd in signed)
        if max_abs <= self.max_wheel_speed:
            return signed

        scale = self.max_wheel_speed / max_abs
        return [cmd * scale for cmd in signed]

    def should_log_wheel_commands(self, wheel_commands: List[float]) -> bool:
        if self.last_logged_wheel_commands is None:
            return True
        return any(
            abs(current - previous) > 1e-4
            for current, previous in zip(wheel_commands, self.last_logged_wheel_commands)
        )


def main() -> None:
    rclpy.init()
    node = MecanumDriveController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
