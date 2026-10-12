#!/usr/bin/env python3
"""Check real scan/map messages and the complete mapping TF chain."""
import argparse
import json
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.time import Time
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import PointCloud2, LaserScan
from tf2_ros import Buffer, TransformListener


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=15)
    args = parser.parse_args()
    rclpy.init()
    node = Node('songwei_mapping_check')
    counts = {'odom': 0, 'cloud': 0, 'scan': 0, 'map': 0}
    last = {}
    def receive(name):
        def cb(msg):
            counts[name] += 1
            last[name] = msg
        return cb
    for name, topic, cls in [('odom', '/odom', Odometry), ('cloud', '/livox/lidar', PointCloud2),
                             ('scan', '/scan', LaserScan)]:
        node.create_subscription(cls, topic, receive(name), qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid, '/map', receive('map'), QoSProfile(
        depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE))
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    start = time.monotonic()
    while time.monotonic() - start < args.seconds:
        rclpy.spin_once(node, timeout_sec=0.1)
    elapsed = time.monotonic() - start
    result = {'domain': __import__('os').environ.get('ROS_DOMAIN_ID'),
              'seconds': round(elapsed, 2), 'messages': counts,
              'hz': {key: round(count / elapsed, 2) for key, count in counts.items()}}
    errors = [f'No {name} messages' for name in counts if not counts[name]]
    if 'scan' in last:
        scan = last['scan']
        finite = [x for x in scan.ranges if math.isfinite(x)]
        expected = int(math.floor((scan.angle_max - scan.angle_min) / scan.angle_increment + 0.5)) + 1
        result['scan'] = {'frame': scan.header.frame_id, 'bins': len(scan.ranges),
                          'expected_karto_bins': expected, 'finite_bins': len(finite),
                          'nearest_m': min(finite) if finite else None}
        if expected != len(scan.ranges):
            errors.append('LaserScan endpoint/bin count mismatch')
        if not finite:
            errors.append('LaserScan contains no finite returns')
    if 'map' in last:
        msg = last['map']
        result['map'] = {'frame': msg.header.frame_id, 'width': msg.info.width,
                         'height': msg.info.height, 'resolution': msg.info.resolution,
                         'known_cells': sum(x >= 0 for x in msg.data),
                         'occupied_cells': sum(x >= 65 for x in msg.data)}
        if not result['map']['known_cells']:
            errors.append('Map has no known cells')
    result['tf'] = {}
    for parent, child in [('map', 'odom'), ('odom', 'base_link'), ('base_link', 'livox_frame')]:
        ok = buffer.can_transform(parent, child, Time())
        result['tf'][f'{parent}->{child}'] = ok
        if not ok:
            errors.append(f'Missing TF {parent}->{child}')
    result['passed'] = not errors
    result['errors'] = errors
    print(json.dumps(result, indent=2))
    node.destroy_node()
    rclpy.shutdown()
    raise SystemExit(0 if not errors else 1)


if __name__ == '__main__':
    main()
