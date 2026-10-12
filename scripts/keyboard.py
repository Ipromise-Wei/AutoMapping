#!/usr/bin/env python3
"""Manual Twist input with bounded speed and a 0.3-second key timeout."""
import select
import signal
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


def main():
    if not sys.stdin.isatty():
        raise SystemExit('请在交互终端运行；SSH 请使用 ssh -t。')
    rclpy.init()
    node = Node('songwei_manual_keyboard')
    publisher = node.create_publisher(Twist, '/songwei/cmd_vel', 10)
    settings = termios.tcgetattr(sys.stdin)
    keys = {'i': (0.15, 0.0, 0.0), ',': (-0.15, 0.0, 0.0),
            'j': (0.0, 0.0, 0.25), 'l': (0.0, 0.0, -0.25),
            'J': (0.0, 0.15, 0.0), 'L': (0.0, -0.15, 0.0)}
    command = (0.0, 0.0, 0.0)
    last_key = 0.0
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        tty.setraw(sys.stdin.fileno())
        while running and rclpy.ok():
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                key = sys.stdin.read(1)
                if key == '\x03':
                    break
                command = keys.get(key, (0.0, 0.0, 0.0))
                last_key = time.monotonic()
            if time.monotonic() - last_key > 0.3:
                command = (0.0, 0.0, 0.0)
            msg = Twist()
            msg.linear.x, msg.linear.y, msg.angular.z = command
            publisher.publish(msg)
            rclpy.spin_once(node, timeout_sec=0)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        for _ in range(3):
            publisher.publish(Twist())
            time.sleep(0.05)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
