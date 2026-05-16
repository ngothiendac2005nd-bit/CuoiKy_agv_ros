#!/usr/bin/env python3

import rclpy
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Imu


class FakeImuFromOdom(Node):
    def __init__(self) -> None:
        super().__init__('fake_imu_from_odom')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('imu_topic', '/imu')
        self.declare_parameter('frame_id', 'base_link')
        self.declare_parameter('gravity', 9.80665)

        odom_topic = str(self.get_parameter('odom_topic').value)
        imu_topic = str(self.get_parameter('imu_topic').value)
        self._frame_id = str(self.get_parameter('frame_id').value)
        self._gravity = float(self.get_parameter('gravity').value)
        self._publisher = self.create_publisher(Imu, imu_topic, 50)
        self.create_subscription(Odometry, odom_topic, self._odom_callback, 50)
        self.get_logger().info(f'Publishing simulated IMU from {odom_topic} to {imu_topic}')

    def _odom_callback(self, msg: Odometry) -> None:
        imu = Imu()
        imu.header.stamp = msg.header.stamp
        imu.header.frame_id = self._frame_id
        imu.orientation = msg.pose.pose.orientation
        imu.angular_velocity = msg.twist.twist.angular
        imu.linear_acceleration.z = self._gravity

        imu.orientation_covariance[0] = 0.01
        imu.orientation_covariance[4] = 0.01
        imu.orientation_covariance[8] = 0.01
        imu.angular_velocity_covariance[0] = 0.01
        imu.angular_velocity_covariance[4] = 0.01
        imu.angular_velocity_covariance[8] = 0.01
        imu.linear_acceleration_covariance[0] = 0.1
        imu.linear_acceleration_covariance[4] = 0.1
        imu.linear_acceleration_covariance[8] = 0.1
        self._publisher.publish(imu)


def main() -> None:
    rclpy.init()
    node = FakeImuFromOdom()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
