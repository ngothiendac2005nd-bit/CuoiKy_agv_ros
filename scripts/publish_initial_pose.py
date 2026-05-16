#!/usr/bin/env python3

import math

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.node import Node


class InitialPosePublisher(Node):
    def __init__(self):
        super().__init__('publish_initial_pose_once')
        self.declare_parameter('x', 0.0)
        self.declare_parameter('y', -1.0)
        self.declare_parameter('yaw', 0.0)
        self.declare_parameter('delay_sec', 1.0)
        self.declare_parameter('repeat_count', 8)

        self.publisher = self.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        delay_sec = float(self.get_parameter('delay_sec').value)
        self.timer = self.create_timer(delay_sec, self.publish_once)
        self.publish_count = 0
        self.repeat_count = int(self.get_parameter('repeat_count').value)

    def publish_once(self):
        if self.publish_count >= self.repeat_count:
            self.timer.cancel()
            return

        yaw = float(self.get_parameter('yaw').value)
        half_yaw = yaw * 0.5

        msg = PoseWithCovarianceStamped()
        # Để stamp = 0 giúp AMCL dùng TF mới nhất hiện có, tránh lỗi extrapolation
        # khi /clock và TF vừa khởi động trong mô phỏng.
        msg.header.frame_id = 'map'
        msg.pose.pose.position.x = float(self.get_parameter('x').value)
        msg.pose.pose.position.y = float(self.get_parameter('y').value)
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation.z = math.sin(half_yaw)
        msg.pose.pose.orientation.w = math.cos(half_yaw)

        msg.pose.covariance[0] = 0.25
        msg.pose.covariance[7] = 0.25
        msg.pose.covariance[35] = 0.06853891909122467

        self.publisher.publish(msg)
        self.get_logger().info(
            f'Published initial pose #{self.publish_count + 1}/{self.repeat_count}: '
            f'x={msg.pose.pose.position.x:.3f}, y={msg.pose.pose.position.y:.3f}, yaw={yaw:.3f}'
        )
        self.publish_count += 1
        if self.publish_count >= self.repeat_count:
            self.timer.cancel()


def main():
    rclpy.init()
    node = InitialPosePublisher()
    while rclpy.ok() and node.publish_count < node.repeat_count:
        rclpy.spin_once(node, timeout_sec=1.0)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
