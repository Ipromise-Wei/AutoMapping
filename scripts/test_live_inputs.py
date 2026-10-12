#!/usr/bin/env python3
"""Read-only test bridge: copy live sensors/odom to an isolated ROS domain.

No publishers of commands, no CAN or LiDAR device access. Only for verification
while the older stack owns the hardware; normal V2 startup does not use this.
"""
import argparse
import json
import signal
import time

import numpy as np
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TransformStamped
from livox_ros_driver2.msg import CustomMsg
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2, PointField
from tf2_ros import TransformBroadcaster


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-domain', type=int, default=30)
    parser.add_argument('--output-domain', type=int, default=31)
    args = parser.parse_args()
    if args.input_domain == args.output_domain:
        parser.error('Domains must differ to avoid republishing into the robot domain')
    incoming, outgoing = Context(), Context()
    incoming.init(domain_id=args.input_domain)
    outgoing.init(domain_id=args.output_domain)
    reader = Node('v2_read_only_sensor_reader', context=incoming)
    writer = Node('v2_read_only_sensor_writer', context=outgoing)
    cloud_pub = writer.create_publisher(PointCloud2, '/livox/lidar', qos_profile_sensor_data)
    odom_pub = writer.create_publisher(Odometry, '/odom', 10)
    tf_pub = TransformBroadcaster(writer)
    counts = {'cloud': 0, 'odom': 0}
    fields = [PointField(name=name, offset=i * 4, datatype=PointField.FLOAT32, count=1)
              for i, name in enumerate(('x', 'y', 'z', 'intensity'))]

    def cloud_cb(msg):
        points = np.array([(p.x, p.y, p.z, p.reflectivity) for p in msg.points], dtype='<f4')
        cloud = PointCloud2(header=msg.header, height=1, width=len(points), fields=fields,
                            is_bigendian=False, point_step=16, row_step=16 * len(points),
                            data=points.tobytes(), is_dense=False)
        cloud_pub.publish(cloud)
        counts['cloud'] += 1

    def odom_cb(msg):
        odom_pub.publish(msg)
        tf = TransformStamped(header=msg.header, child_frame_id=msg.child_frame_id)
        tf.transform.translation.x = msg.pose.pose.position.x
        tf.transform.translation.y = msg.pose.pose.position.y
        tf.transform.translation.z = msg.pose.pose.position.z
        tf.transform.rotation = msg.pose.pose.orientation
        tf_pub.sendTransform(tf)
        counts['odom'] += 1

    reader.create_subscription(CustomMsg, '/livox/lidar', cloud_cb, qos_profile_sensor_data)
    reader.create_subscription(Odometry, '/odom', odom_cb, qos_profile_sensor_data)
    executor = SingleThreadedExecutor(context=incoming)
    executor.add_node(reader)
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(json.dumps({'read_domain': args.input_domain, 'write_domain': args.output_domain,
                      'topics': ['/livox/lidar', '/odom', '/tf'], 'commands': []}), flush=True)
    deadline = time.monotonic() + 10
    try:
        while running:
            executor.spin_once(timeout_sec=0.1)
            if time.monotonic() >= deadline:
                print(json.dumps(counts), flush=True)
                deadline += 10
    finally:
        executor.shutdown()
        reader.destroy_node()
        writer.destroy_node()
        incoming.shutdown()
        outgoing.shutdown()


if __name__ == '__main__':
    main()
