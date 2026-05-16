#!/usr/bin/env python3

import math
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple

import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header
from tf2_ros import Buffer, TransformException, TransformListener
from tf2_sensor_msgs.tf2_sensor_msgs import do_transform_cloud


VoxelKey = Tuple[int, int, int]
StoredPoint = Tuple[float, float, float, float, int]
PoseState = Tuple[float, float, float, float, float, float, float]


class AccumulatePointCloudMap(Node):
    def __init__(self) -> None:
        super().__init__('accumulate_pointcloud_map')
        self.declare_parameter('input_topic', '/scan_matched_points2')
        self.declare_parameter('fallback_input_topic', '/points2')
        self.declare_parameter('output_topic', '/accumulated_points2')
        self.declare_parameter('fixed_frame', 'odom')
        self.declare_parameter('pose_frame', 'base_link')
        self.declare_parameter('voxel_size', 0.05)
        self.declare_parameter('min_z', -0.2)
        self.declare_parameter('max_z', 2.5)
        self.declare_parameter('publish_period', 0.5)
        self.declare_parameter('transform_timeout', 0.2)
        self.declare_parameter('max_published_points', 250000)
        self.declare_parameter('fallback_to_latest_transform', True)
        self.declare_parameter('status_period', 3.0)
        self.declare_parameter('state_file', '')
        self.declare_parameter('load_existing', True)
        self.declare_parameter('autosave_period', 5.0)
        self.declare_parameter('use_motion_filter', True)
        self.declare_parameter('min_translation', 0.08)
        self.declare_parameter('min_rotation', 0.08)
        self.declare_parameter('matched_topic_grace_period', 0.75)

        self._input_topic = str(self.get_parameter('input_topic').value)
        self._fallback_input_topic = str(self.get_parameter('fallback_input_topic').value)
        self._output_topic = str(self.get_parameter('output_topic').value)
        self._fixed_frame = str(self.get_parameter('fixed_frame').value)
        self._pose_frame = str(self.get_parameter('pose_frame').value)
        self._voxel_size = float(self.get_parameter('voxel_size').value)
        self._min_z = float(self.get_parameter('min_z').value)
        self._max_z = float(self.get_parameter('max_z').value)
        self._transform_timeout = float(self.get_parameter('transform_timeout').value)
        self._max_published_points = int(self.get_parameter('max_published_points').value)
        self._fallback_to_latest_transform = bool(self.get_parameter('fallback_to_latest_transform').value)
        self._state_file = Path(str(self.get_parameter('state_file').value)).expanduser()
        self._load_existing = bool(self.get_parameter('load_existing').value)
        self._use_motion_filter = bool(self.get_parameter('use_motion_filter').value)
        self._min_translation = float(self.get_parameter('min_translation').value)
        self._min_rotation = float(self.get_parameter('min_rotation').value)
        self._matched_topic_grace_period = float(self.get_parameter('matched_topic_grace_period').value)
        self._voxels: Dict[VoxelKey, StoredPoint] = {}
        self._last_pose_state: Optional[PoseState] = None
        self._received_clouds = 0
        self._used_clouds = 0
        self._dropped_clouds = 0
        self._new_voxels_since_status = 0
        self._dirty = False
        self._last_matched_stamp: Optional[Time] = None

        input_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        output_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._publisher = self.create_publisher(PointCloud2, self._output_topic, output_qos)
        self.create_subscription(
            PointCloud2,
            self._input_topic,
            lambda msg: self._cloud_callback(msg, source='matched'),
            input_qos,
        )
        if self._fallback_input_topic and self._fallback_input_topic != self._input_topic:
            self.create_subscription(
                PointCloud2,
                self._fallback_input_topic,
                lambda msg: self._cloud_callback(msg, source='raw'),
                input_qos,
            )
        self.create_timer(float(self.get_parameter('publish_period').value), self._publish_cloud)
        self.create_timer(float(self.get_parameter('status_period').value), self._publish_status)
        autosave_period = float(self.get_parameter('autosave_period').value)
        if autosave_period > 0.0 and str(self._state_file):
            self.create_timer(autosave_period, self._autosave_state)
        if self._load_existing and str(self._state_file):
            self._restore_state()
        self.get_logger().info(
            f'Accumulating {self._input_topic} with fallback {self._fallback_input_topic} '
            f'into {self._output_topic} in frame {self._fixed_frame} using pose frame {self._pose_frame}'
        )

    def _cloud_callback(self, msg: PointCloud2, source: str) -> None:
        self._received_clouds += 1
        stamp = Time.from_msg(msg.header.stamp)
        if source == 'raw' and self._should_skip_raw_cloud(stamp):
            return
        if source == 'matched':
            self._last_matched_stamp = stamp
        try:
            transform = self._tf_buffer.lookup_transform(
                self._fixed_frame,
                msg.header.frame_id,
                msg.header.stamp,
                timeout=Duration(seconds=self._transform_timeout),
            )
        except TransformException as exc:
            if not self._fallback_to_latest_transform:
                self._dropped_clouds += 1
                self.get_logger().warn(f'Skipping cloud without timestamped transform: {exc}', throttle_duration_sec=2.0)
                return
            try:
                transform = self._tf_buffer.lookup_transform(
                    self._fixed_frame,
                    msg.header.frame_id,
                    Time(),
                    timeout=Duration(seconds=self._transform_timeout),
                )
            except TransformException as latest_exc:
                self._dropped_clouds += 1
                self.get_logger().warn(
                    f'Skipping cloud without latest transform: {latest_exc}',
                    throttle_duration_sec=2.0,
                )
                return

        cloud = do_transform_cloud(msg, transform)
        current_pose_state = self._lookup_pose_state(msg.header.stamp)
        if current_pose_state is None:
            self._dropped_clouds += 1
            return
        if self._use_motion_filter and not self._should_accept_pose(current_pose_state):
            return
        self._used_clouds += 1

        field_names = [field.name for field in cloud.fields]
        read_fields = ['x', 'y', 'z']
        has_intensity = 'intensity' in field_names
        if has_intensity:
            read_fields.append('intensity')

        added = 0
        for point in point_cloud2.read_points(cloud, field_names=read_fields, skip_nans=True):
            x = float(point[0])
            y = float(point[1])
            z = float(point[2])
            if not math.isfinite(x) or not math.isfinite(y) or not math.isfinite(z):
                continue
            if z < self._min_z or z > self._max_z:
                continue
            intensity = float(point[3]) if has_intensity and len(point) > 3 else z
            key = (
                int(math.floor(x / self._voxel_size)),
                int(math.floor(y / self._voxel_size)),
                int(math.floor(z / self._voxel_size)),
            )
            if key not in self._voxels:
                added += 1
                self._voxels[key] = (x, y, z, intensity, 1)
            else:
                prev_x, prev_y, prev_z, prev_i, prev_n = self._voxels[key]
                new_n = prev_n + 1
                self._voxels[key] = (
                    prev_x + (x - prev_x) / new_n,
                    prev_y + (y - prev_y) / new_n,
                    prev_z + (z - prev_z) / new_n,
                    prev_i + (intensity - prev_i) / new_n,
                    new_n,
                )

        self._new_voxels_since_status += added
        self._dirty = True
        self._last_pose_state = current_pose_state

    def _should_skip_raw_cloud(self, stamp: Time) -> bool:
        if self._last_matched_stamp is None:
            return False
        age = (stamp.nanoseconds - self._last_matched_stamp.nanoseconds) / 1e9
        return age <= self._matched_topic_grace_period

    def _lookup_pose_state(self, stamp) -> Optional[PoseState]:
        try:
            pose_transform = self._tf_buffer.lookup_transform(
                self._fixed_frame,
                self._pose_frame,
                stamp,
                timeout=Duration(seconds=self._transform_timeout),
            )
        except TransformException as exc:
            if not self._fallback_to_latest_transform:
                self.get_logger().warn(
                    f'Skipping cloud without pose transform for {self._pose_frame}: {exc}',
                    throttle_duration_sec=2.0,
                )
                return None
            try:
                pose_transform = self._tf_buffer.lookup_transform(
                    self._fixed_frame,
                    self._pose_frame,
                    Time(),
                    timeout=Duration(seconds=self._transform_timeout),
                )
            except TransformException as latest_exc:
                self.get_logger().warn(
                    f'Skipping cloud without latest pose transform for {self._pose_frame}: {latest_exc}',
                    throttle_duration_sec=2.0,
                )
                return None
        return self._pose_state_from_transform(pose_transform)

    def _publish_cloud(self) -> None:
        if not self._voxels:
            return

        points = [(x, y, z, intensity) for x, y, z, intensity, _count in self._voxels.values()]
        if len(points) > self._max_published_points:
            step = max(1, len(points) // self._max_published_points)
            points = points[::step]

        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self._fixed_frame
        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='intensity', offset=12, datatype=PointField.FLOAT32, count=1),
        ]
        self._publisher.publish(point_cloud2.create_cloud(header, fields, points))

    def _publish_status(self) -> None:
        self.get_logger().info(
            'Accumulated map status: '
            f'clouds received={self._received_clouds}, used={self._used_clouds}, dropped={self._dropped_clouds}, '
            f'voxels={len(self._voxels)}, new_voxels_recent={self._new_voxels_since_status}'
        )
        self._new_voxels_since_status = 0

    def _pose_state_from_transform(self, transform) -> PoseState:
        translation = transform.transform.translation
        rotation = transform.transform.rotation
        return (
            float(translation.x),
            float(translation.y),
            float(translation.z),
            float(rotation.x),
            float(rotation.y),
            float(rotation.z),
            float(rotation.w),
        )

    def _should_accept_pose(self, current_pose: PoseState) -> bool:
        if self._last_pose_state is None:
            return True
        dx = current_pose[0] - self._last_pose_state[0]
        dy = current_pose[1] - self._last_pose_state[1]
        dz = current_pose[2] - self._last_pose_state[2]
        translation = math.sqrt(dx * dx + dy * dy + dz * dz)
        q1 = self._last_pose_state[3:]
        q2 = current_pose[3:]
        dot = abs(sum(a * b for a, b in zip(q1, q2)))
        dot = max(-1.0, min(1.0, dot))
        rotation = 2.0 * math.acos(dot)
        return translation >= self._min_translation or rotation >= self._min_rotation

    def _restore_state(self) -> None:
        if not self._state_file.exists():
            return
        try:
            with self._state_file.open('rb') as handle:
                state = pickle.load(handle)
            if state.get('fixed_frame') != self._fixed_frame:
                self.get_logger().warn(
                    f'Ignoring saved state because fixed_frame={state.get("fixed_frame")} '
                    f'!= current {self._fixed_frame}'
                )
                return
            self._voxels = state.get('voxels', {})
            self.get_logger().info(
                f'Restored {len(self._voxels)} voxels from {self._state_file}'
            )
        except Exception as exc:
            self.get_logger().warn(f'Failed to restore accumulated state: {exc}')

    def _autosave_state(self) -> None:
        if not self._dirty or not str(self._state_file):
            return
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            with self._state_file.open('wb') as handle:
                pickle.dump(
                    {
                        'fixed_frame': self._fixed_frame,
                        'voxels': self._voxels,
                    },
                    handle,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
            self._dirty = False
        except Exception as exc:
            self.get_logger().warn(f'Failed to save accumulated state: {exc}')


def main() -> None:
    rclpy.init()
    node = AccumulatePointCloudMap()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node._autosave_state()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
