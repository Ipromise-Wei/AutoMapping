#!/usr/bin/env python3
"""Deskew MID-360 points using wheel odometry and remove chassis returns."""
from collections import deque
import copy
import signal
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2, PointField


def cloud_arrays(msg):
    types = {1: 'i1', 2: 'u1', 3: '<i2', 4: '<u2', 5: '<i4',
             6: '<u4', 7: '<f4', 8: '<f8'}
    if msg.is_bigendian or msg.height != 1:
        raise ValueError('Expected little-endian unorganized MID-360 cloud')
    dtype = np.dtype({'names': [f.name for f in msg.fields],
                      'formats': [types[f.datatype] for f in msg.fields],
                      'offsets': [f.offset for f in msg.fields], 'itemsize': msg.point_step})
    points = np.frombuffer(msg.data, dtype=dtype, count=msg.width)
    if not {'x', 'y', 'z', 'timestamp'}.issubset(points.dtype.names):
        raise ValueError('MID-360 point timestamps are required for motion compensation')
    header = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
    if len(points) == 0:
        return points, np.empty(0)
    stamps = points['timestamp'].astype(np.float64)
    # Current official driver carries absolute nanoseconds in timestamp.
    # Earlier versions may carry nanosecond offsets relative to the header.
    stamps = stamps * 1e-9 if np.median(stamps) > 1e12 else header + stamps * 1e-9
    if not np.all(np.isfinite(stamps)) or np.max(np.abs(stamps - header)) > 0.5:
        raise ValueError('Point timestamps disagree with the cloud header')
    return points, stamps


def mount_rotation(rpy):
    roll, pitch, yaw = rpy
    cr, sr, cp, sp, cy, sy = (np.cos(roll), np.sin(roll), np.cos(pitch),
                             np.sin(pitch), np.cos(yaw), np.sin(yaw))
    return np.array([[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
                     [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr],
                     [-sp, cp*sr, cp*cr]])


def compensate(points, stamps, odom, xyz, rpy, self_x, self_y):
    """Return points in base_link at the final point's timestamp."""
    reference = float(np.max(stamps))
    # Absolute nanoseconds stored in float64 are quantized by about 256 ns
    # at current Unix dates; allow 1 us at the interpolation endpoints.
    if odom[0, 0] > np.min(stamps) + 1e-6 or odom[-1, 0] < reference - 1e-6:
        raise ValueError('Odometry does not cover the complete point acquisition interval')
    body = np.column_stack((points['x'], points['y'], points['z'])).astype(np.float64)
    body = body @ mount_rotation(rpy).T + np.asarray(xyz)
    valid = np.all(np.isfinite(body), axis=1)
    valid &= ~((np.abs(body[:, 0]) <= self_x) & (np.abs(body[:, 1]) <= self_y))
    if 'tag' in points.dtype.names:
        # Livox confidence group: retain normal/high-confidence returns.
        valid &= (points['tag'] & 0x30) < 0x20
    body, stamps, points = body[valid], stamps[valid], points[valid]
    headings = np.unwrap(odom[:, 3])
    angle = np.interp(stamps, odom[:, 0], headings)
    px = np.interp(stamps, odom[:, 0], odom[:, 1])
    py = np.interp(stamps, odom[:, 0], odom[:, 2])
    ref_x = np.interp(reference, odom[:, 0], odom[:, 1])
    ref_y = np.interp(reference, odom[:, 0], odom[:, 2])
    ref_angle = np.interp(reference, odom[:, 0], headings)
    c, s = np.cos(angle), np.sin(angle)
    world_x = c*body[:, 0] - s*body[:, 1] + px - ref_x
    world_y = s*body[:, 0] + c*body[:, 1] + py - ref_y
    rc, rs = np.cos(ref_angle), np.sin(ref_angle)
    output = np.zeros((len(body), 4), dtype='<f4')
    output[:, 0] = rc*world_x + rs*world_y
    output[:, 1] = -rs*world_x + rc*world_y
    output[:, 2] = body[:, 2]
    if 'intensity' in points.dtype.names:
        output[:, 3] = points['intensity']
    return output, reference, int(np.count_nonzero(~valid))


class CloudPreprocessor(Node):
    def __init__(self):
        super().__init__('mid360_motion_compensation')
        self.xyz = self.declare_parameter('lidar_xyz', [0.35, 0.0, 0.10]).value
        self.rpy = self.declare_parameter('lidar_rpy', [0.0, 0.0, 0.0]).value
        self.self_x = self.declare_parameter('self_filter_x', 0.43).value
        self.self_y = self.declare_parameter('self_filter_y', 0.32).value
        self.odom = deque(maxlen=1000)
        self.pending = deque()
        self.last_warning = 0.0
        self.fields = [PointField(name=name, offset=4*i, datatype=PointField.FLOAT32, count=1)
                       for i, name in enumerate(('x', 'y', 'z', 'intensity'))]
        self.publisher = self.create_publisher(PointCloud2, '/songwei/cloud_deskewed', qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', self.odom_callback, qos_profile_sensor_data)
        self.create_subscription(PointCloud2, '/livox/lidar', self.cloud_callback, qos_profile_sensor_data)
        self.get_logger().info('MID-360 per-point motion compensation and chassis filtering enabled')

    def warn(self, message):
        if time.monotonic() - self.last_warning > 5:
            self.get_logger().warn(message)
            self.last_warning = time.monotonic()

    def odom_callback(self, msg):
        q = msg.pose.pose.orientation
        heading = np.arctan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec*1e-9
        if self.odom and stamp <= self.odom[-1][0]:
            if stamp < self.odom[-1][0]:
                self.odom.clear()
                self.pending.clear()
            else:
                return
        p = msg.pose.pose.position
        self.odom.append((stamp, p.x, p.y, heading))
        self.flush()

    def cloud_callback(self, msg):
        try:
            points, stamps = cloud_arrays(msg)
            if not len(points):
                return
        except ValueError as error:
            self.warn(str(error))
            return
        self.pending.append((msg, points, stamps, time.monotonic()))
        while len(self.pending) > 5:
            self.pending.popleft()
            self.warn('Discarding cloud because matching odometry is unavailable')
        self.flush()

    def flush(self):
        while self.pending and len(self.odom) >= 2:
            msg, points, stamps, arrival = self.pending[0]
            if self.odom[0][0] > np.min(stamps) + 1e-6:
                self.pending.popleft()
                continue
            if self.odom[-1][0] < np.max(stamps) - 1e-6:
                if time.monotonic() - arrival > 0.5:
                    self.pending.popleft()
                    self.warn('Odometry is late; discarding cloud rather than extrapolating')
                    continue
                return
            self.pending.popleft()
            output, reference, removed = compensate(points, stamps, np.asarray(self.odom),
                                                     self.xyz, self.rpy, self.self_x, self.self_y)
            header = copy.deepcopy(msg.header)
            header.frame_id = 'base_link'
            nanos = round(reference*1e9)
            header.stamp.sec, header.stamp.nanosec = divmod(nanos, 1000000000)
            self.publisher.publish(PointCloud2(header=header, height=1, width=len(output),
                fields=self.fields, is_bigendian=False, point_step=16,
                row_step=16*len(output), data=output.tobytes(), is_dense=True))


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = CloudPreprocessor()
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while not stopping and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
