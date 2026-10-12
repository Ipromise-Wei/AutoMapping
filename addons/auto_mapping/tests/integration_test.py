#!/usr/bin/env python3
"""Real SLAM/Nav2/frontier integration, synthetic scan/odom, isolated domain 31.

No map is published by this test and no physical drivers are launched.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import re
import subprocess
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import Twist, TransformStamped, PoseStamped
from nav_msgs.msg import Odometry, OccupancyGrid, Path as RosPath
from sensor_msgs.msg import LaserScan
from action_msgs.msg import GoalStatusArray
from lifecycle_msgs.srv import GetState
from tf2_ros import TransformBroadcaster

assert os.environ.get('ROS_DOMAIN_ID') == '31'
assert os.environ.get('ROS_LOCALHOST_ONLY') == '1'
parser = argparse.ArgumentParser()
parser.add_argument('--rviz', action='store_true')
parser.add_argument('--autostart', action='store_true')
parser.add_argument('--wait-cycle', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
project = root.parents[1]
logs = root / 'logs'
logs.mkdir(exist_ok=True)
rclpy.init()
node = Node('isolated_auto_mapping_test_robot')
pose = [0., 0., 0.]
cmd = [0., 0.]
commands, goals, maps, paths, statuses, trace = [], [], [], [], [], []
odom_pub = node.create_publisher(Odometry, '/odom', 10)
scan_pub = node.create_publisher(LaserScan, '/scan', qos_profile_sensor_data)
broadcaster = TransformBroadcaster(node)


def command_cb(msg):
    cmd[:] = [msg.linear.x, msg.angular.z]
    commands.append([time.monotonic(), *cmd])


node.create_subscription(Twist, '/songwei/cmd_vel', command_cb, 10)
node.create_subscription(PoseStamped, '/auto_mapping/selected_frontier',
    lambda m: goals.append([m.pose.position.x, m.pose.position.y]), 10)
node.create_subscription(OccupancyGrid, '/map',
    lambda m: maps.append({'known': sum(v >= 0 for v in m.data), 'width': m.info.width,
                          'height': m.info.height, 'time': time.monotonic()}),
    QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
node.create_subscription(RosPath, '/plan', lambda m: paths.append(len(m.poses)), 10)
node.create_subscription(GoalStatusArray, '/navigate_to_pose/_action/status',
    lambda m: statuses.extend(s.status for s in m.status_list),
    QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL))
last = [time.monotonic()]


def odom_tick():
    now = time.monotonic()
    dt = min(now-last[0], .1)
    last[0] = now
    v, w = cmd
    if abs(w) > 1e-8:
        radius = abs(v/w)
        if radius < .47644:
            v = 0.
        else:
            factor = math.cos(math.atan(.494/(2*radius)))
            v *= factor
            w *= factor
    pose[0] += v*math.cos(pose[2]+w*dt/2)*dt
    pose[1] += v*math.sin(pose[2]+w*dt/2)*dt
    pose[2] += w*dt
    msg = Odometry()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.header.frame_id = 'odom'
    msg.child_frame_id = 'base_link'
    msg.pose.pose.position.x, msg.pose.pose.position.y = pose[:2]
    msg.pose.pose.orientation.z = math.sin(pose[2]/2)
    msg.pose.pose.orientation.w = math.cos(pose[2]/2)
    msg.twist.twist.linear.x, msg.twist.twist.angular.z = v, w
    odom_pub.publish(msg)
    tf = TransformStamped(header=msg.header, child_frame_id='base_link')
    tf.transform.translation.x, tf.transform.translation.y = pose[:2]
    tf.transform.rotation = msg.pose.pose.orientation
    broadcaster.sendTransform(tf)


def scan_tick():
    angles = -2.35619449 + np.arange(270)*.017511664734 + pose[2]
    distances = np.arange(.3, 12.001, .025)
    xs = pose[0] + np.cos(angles)[:, None]*distances
    ys = pose[1] + np.sin(angles)[:, None]*distances
    # Room and occluding partition: exploration must reveal previously unseen space.
    occupied = ((xs < -2) | (xs > 6) | (ys < -2) | (ys > 3)
                | ((xs > 1.45) & (xs < 1.6) & (ys < .6)))
    ranges = distances[occupied.argmax(axis=1)]
    ranges[~occupied.any(axis=1)] = np.inf
    msg = LaserScan()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.header.frame_id = 'base_link'
    msg.angle_min, msg.angle_max, msg.angle_increment = -2.35619449, 2.35619449, .017511664734
    msg.range_min, msg.range_max, msg.scan_time = .3, 12., .1
    msg.ranges = ranges.tolist()
    scan_pub.publish(msg)


node.create_timer(.02, odom_tick)
node.create_timer(.1, scan_tick)


def spin(seconds):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=.01)
    trace.append({'time': time.monotonic(), 'pose': list(pose), 'cmd': list(cmd),
                  'known': maps[-1]['known'] if maps else 0})


def run_script(name, arguments=(), timeout=35):
    with (logs / ('test_' + name + '.log')).open('w') as out:
        child = subprocess.Popen([str(root/'scripts'/name), *arguments], stdout=out,
                                 stderr=subprocess.STDOUT)
        deadline = time.monotonic()+timeout
        while child.poll() is None and time.monotonic() < deadline:
            spin(.05)
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
            raise AssertionError('Script timed out: ' + name)
        assert child.returncode == 0, (name, (logs/('test_'+name+'.log')).read_text())


log = (logs/'integration_launch.log').open('w')
process = subprocess.Popen(['ros2', 'launch', 'songwei_auto_mapping', 'auto_mapping.launch.py',
    'start_base:=false', 'start_lidar:=false', 'autostart:=' + str(args.autostart).lower(),
    'rviz:=' + str(args.rviz).lower()], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
(logs/'session_31.pid').write_text(str(process.pid))
name = 'auto_mapping_test_' + str(process.pid)
report = {'passed': False, 'domain': 31, 'physical_hardware_started': False}
try:
    state = node.create_client(GetState, '/bt_navigator/get_state')
    deadline = time.monotonic()+45
    while time.monotonic() < deadline:
        spin(.3)
        if maps and state.service_is_ready():
            future = state.call_async(GetState.Request())
            while not future.done():
                spin(.05)
            if future.result().current_state.id == 3:
                break
    else:
        raise AssertionError('Real SLAM/Nav2 failed to start')
    nodes = node.get_node_names()
    assert 'amcl' not in nodes and 'map_server' not in nodes, nodes
    assert 'ranger_base_node' not in nodes and 'livox_lidar_publisher' not in nodes, nodes
    assert nodes.count('slam_toolbox') == 1 and nodes.count('frontier_explorer') == 1, nodes
    spin(2)
    if not args.autostart:
        assert not goals and not any(abs(v)+abs(w) > .001 for _,v,w in commands), 'Paused startup moved'
    known_before = maps[-1]['known']
    if not args.autostart:
        run_script('resume.sh', timeout=95)
    deadline = time.monotonic()+120
    while time.monotonic() < deadline:
        spin(.2)
        if (goals and paths and math.hypot(*pose[:2]) > .6
                and maps[-1]['known'] > known_before + 200
                and (not args.wait_cycle or (len(goals) >= 2 and
                     'active frontier considered complete by goal_preemption_complete_if_within_m'
                     in (logs/'integration_launch.log').read_text()))):
            break
    else:
        raise AssertionError(('No autonomous motion/map growth', goals, pose, maps[-1], known_before))
    assert min(v for _,v,_ in commands) >= -.00001
    assert max(v for _,v,_ in commands) <= .15001
    assert max(abs(w) for _,_,w in commands) <= .30001
    if args.rviz:
        windows = subprocess.check_output(['xwininfo','-root','-tree'], text=True)
        window_ids = [re.search(r'(0x[0-9a-f]+)',line).group(1) for line in windows.splitlines()
                      if 'auto_mapping.rviz - RViz' in line]
        assert len(window_ids) == 1, windows
        subprocess.run(['/usr/bin/python3',str(project/'logs/capture_rviz.py'),window_ids[0],
                        str(logs/'auto_mapping_rviz.png')],check=True)
    run_script('pause.sh')
    paused_goals, paused_pose = len(goals), list(pose)
    spin(2)
    assert len(goals) == paused_goals and max(abs(x) for x in cmd) < .001
    assert math.dist(paused_pose[:2], pose[:2]) < .01
    run_script('resume.sh', timeout=95)
    deadline = time.monotonic()+25
    while time.monotonic() < deadline and len(goals) == paused_goals:
        spin(.1)
    assert len(goals) > paused_goals, 'Resume failed to dispatch a fresh goal'
    run_script('save_map.sh', [name], timeout=60)
    assert max(abs(x) for x in cmd) < .001
    for suffix in ('yaml', 'pgm', 'posegraph', 'data'):
        assert (project/'maps'/f'{name}.{suffix}').stat().st_size > 0
    checked = subprocess.run(['/usr/bin/python3', str(project/'scripts/resolve_map.py'), name],
                             capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
    if args.rviz:
        assert 'auto_mapping_rviz' in node.get_node_names()
    run_script('stop.sh', timeout=55)
    spin(1)
    assert process.poll() is not None
    residual = set(node.get_node_names()) & {'slam_toolbox', 'controller_server', 'bt_navigator',
                                           'frontier_explorer', 'ranger_base_node'}
    assert not residual, residual
    report.update(passed=True, no_saved_map_or_AMCL=True,
        paused_startup_stationary=not args.autostart, automatic_start=args.autostart,
        autonomous_goal_succeeded=4 in statuses,
        frontier_proximity_completion=('active frontier considered complete by goal_preemption_complete_if_within_m'
                                      in (logs/'integration_launch.log').read_text()),
        autonomous_goals=len(goals), path_points=max(paths), initial_known_cells=known_before,
        final_known_cells=max(m['known'] for m in maps), final_pose=pose,
        max_forward_mps=max(v for _,v,_ in commands), max_angular_radps=max(abs(w) for _,_,w in commands),
        pause_cancels_and_stops=True, resume_dispatches=True, map_saved_four_files=True,
        map_accepted_by_original_navigation=True, stop_cleans_processes=True,
        rviz_started=args.rviz, action_statuses=sorted(set(statuses)))
finally:
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
    target = logs/'test_maps'
    target.mkdir(exist_ok=True)
    for suffix in ('yaml','pgm','posegraph','data'):
        p = project/'maps'/f'{name}.{suffix}'
        if p.exists():
            p.rename(target/p.name)
    report['saved_test_map'] = str(target/f'{name}.yaml')
    (logs/'integration_report.json').write_text(json.dumps(report, indent=2))
    (logs/'integration_trace.json').write_text(json.dumps({'trace':trace,'goals':goals,'maps':maps},indent=2))
    log.close()
    node.destroy_node()
    rclpy.shutdown()
print(json.dumps(report, indent=2))
