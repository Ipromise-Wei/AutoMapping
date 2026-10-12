#!/usr/bin/env python3
"""Gate startup on actual SLAM/Nav2 readiness and confirm pause before map saving."""
import argparse
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from rclpy.utilities import remove_ros_args
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from sensor_msgs.msg import LaserScan
from lifecycle_msgs.srv import GetState
from frontier_exploration_ros2.srv import ControlExploration
from tf2_ros import Buffer, TransformListener


class Control(Node):
    def __init__(self):
        super().__init__('auto_mapping_control')
        self.client = self.create_client(ControlExploration, '/auto_mapping/control_exploration')
        self.map_ready = False
        self.costmap_ready = False
        self.scan_time = 0.
        self.odom_time = 0.
        self.cmd_time = 0.
        self.odom_speed = float('inf')
        self.command_speed = float('inf')
        self.zero = self.create_publisher(Twist, '/songwei/nav_cmd_vel', 10)
        self.create_subscription(OccupancyGrid, '/map', self.map_cb,
                                 QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(OccupancyGrid, '/global_costmap/costmap', self.costmap_cb, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_cb, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', self.odom_cb, qos_profile_sensor_data)
        self.create_subscription(Twist, '/songwei/cmd_vel', self.command_cb, 10)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.states = {name: self.create_client(GetState, '/' + name + '/get_state') for name in
                       ('controller_server', 'planner_server', 'behavior_server',
                        'bt_navigator', 'velocity_smoother')}

    def map_cb(self, msg):
        self.map_ready = msg.header.frame_id == 'map' and any(0 <= v < 50 for v in msg.data)

    def costmap_cb(self, msg):
        self.costmap_ready = msg.header.frame_id == 'map' and len(msg.data) > 0

    def scan_cb(self, msg):
        if msg.ranges:
            self.scan_time = time.monotonic()

    def odom_cb(self, msg):
        self.odom_time = time.monotonic()
        self.odom_speed = max(abs(msg.twist.twist.linear.x), abs(msg.twist.twist.linear.y),
                              abs(msg.twist.twist.angular.z))

    def command_cb(self, msg):
        self.cmd_time = time.monotonic()
        self.command_speed = max(abs(msg.linear.x), abs(msg.linear.y), abs(msg.angular.z))

    def spin(self, seconds):
        end = time.monotonic() + seconds
        while rclpy.ok() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=.05)

    def request(self, client, req, timeout=3.):
        if not client.service_is_ready():
            raise RuntimeError('服务尚未就绪：' + client.srv_name)
        # Fast DDS can discover a request endpoint before the response path is
        # ready. These immediate START/STOP and GetState requests are idempotent.
        for attempt in range(3):
            future = client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
            if future.done() and not future.exception():
                return future.result()
            client.remove_pending_request(future)
            if attempt < 2:
                self.get_logger().warning('服务回复超时，正在有限重试：' + client.srv_name)
                self.spin(.3)
        raise RuntimeError('服务响应超时或失败：' + client.srv_name)

    def explorer_request(self, action):
        req = ControlExploration.Request()
        req.action = action
        reply = self.request(self.client, req)
        if not reply.accepted:
            raise RuntimeError(reply.message)
        return reply

    def start(self):
        self.get_logger().info('等待 SLAM 地图、扫描、TF 和 Nav2 激活；就绪后启动自动探索。')
        deadline = time.monotonic() + 90.
        while time.monotonic() < deadline and rclpy.ok():
            self.spin(.2)
            if not (self.map_ready and self.costmap_ready and self.client.service_is_ready()
                    and time.monotonic() - self.scan_time < 1.
                    and time.monotonic() - self.odom_time < 1.
                    and self.buffer.can_transform('map', 'base_link', rclpy.time.Time())):
                continue
            if not all(c.service_is_ready() for c in self.states.values()):
                continue
            if not all(self.request(c, GetState.Request()).current_state.id == 3
                       for c in self.states.values()):
                continue
            self.explorer_request(ControlExploration.Request.ACTION_START)
            self.get_logger().info('自动探索已启动；暂停使用 addons/auto_mapping/scripts/pause.sh。')
            return
        raise RuntimeError('90 秒内 SLAM/Nav2 未就绪，未启动自动探索。检查启动日志和雷达/里程计。')

    def pause(self):
        if not self.client.wait_for_service(timeout_sec=5.):
            raise RuntimeError('未找到本模块控制服务；请确认自动建图已启动且 ROS_DOMAIN_ID 一致。')
        deadline = time.monotonic() + 15.
        while time.monotonic() < deadline:
            response = self.explorer_request(ControlExploration.Request.ACTION_STOP)
            if response.state == ControlExploration.Request.STATE_IDLE:
                break
            self.spin(.2)
        else:
            raise RuntimeError('探索目标取消尚未完成，不执行地图保存。请检查启动终端。')
        # The explorer is now idle and has finished cancelling its Nav2 action.
        # Feed zero through the existing smoother, and observe both output and odometry.
        stationary_since = None
        deadline = time.monotonic() + 6.
        while time.monotonic() < deadline:
            self.zero.publish(Twist())
            self.spin(.05)
            now = time.monotonic()
            if (now - self.odom_time < .5 and now - self.cmd_time < .5
                    and self.odom_speed < .02 and self.command_speed < .001):
                stationary_since = stationary_since or now
                if now - stationary_since >= .5:
                    self.get_logger().info('探索已暂停，目标已取消，已确认零速度和车辆静止；SLAM 继续运行。')
                    return
            else:
                stationary_since = None
        raise RuntimeError('探索已暂停，但未确认车辆静止；请检查里程计、遥控器状态，暂不保存。')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'pause'])
    args = parser.parse_args(remove_ros_args(sys.argv)[1:])
    rclpy.init()
    node = Control()
    try:
        getattr(node, args.action)()
    except (RuntimeError, KeyboardInterrupt) as error:
        node.get_logger().error(str(error))
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
