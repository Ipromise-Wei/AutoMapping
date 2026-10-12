import os
import xml.etree.ElementTree as ET

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler, EmitEvent
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    share = get_package_share_directory('songwei_bringup')
    def value(name):
        return LaunchConfiguration(name).perform(context)
    with open(value('robot_config'), encoding='utf-8') as stream:
        robot = yaml.safe_load(stream)
    sim = value('use_sim_time').lower() == 'true'
    xml = ET.parse(os.path.join(share, 'urdf', 'ranger_visual.urdf'))
    origin = xml.find("./joint[@name='lidar_mount']/origin")
    origin.set('xyz', ' '.join(str(x) for x in robot['lidar_xyz']))
    origin.set('rpy', ' '.join(str(x) for x in robot['lidar_rpy']))

    # Connect the official driver to a dedicated command topic. Only the
    # explicit keyboard launcher publishes here; old Nav2 /cmd_vel cannot drive it.
    base = Node(
        package='ranger_base', executable='ranger_base_node', name='ranger_base_node',
        condition=IfCondition(LaunchConfiguration('start_base')),
        parameters=[{'robot_model': 'ranger_mini_v3', 'port_name': robot['can_device'],
                     'base_frame': 'base_link', 'odom_frame': 'odom',
                     'odom_topic_name': 'odom', 'publish_odom_tf': True,
                     'update_rate': 50, 'use_sim_time': sim}],
        remappings=[('/cmd_vel', '/songwei/cmd_vel')], output='screen')
    lidar = Node(
        package='livox_ros_driver2', executable='livox_ros_driver2_node',
        name='livox_lidar_publisher', condition=IfCondition(LaunchConfiguration('start_lidar')),
        parameters=[{'xfer_format': 0, 'multi_topic': 0, 'data_src': 0,
                     'publish_freq': 10.0, 'output_data_type': 0,
                     'frame_id': 'livox_frame', 'user_config_path': value('lidar_config'),
                     'cmdline_input_bd_code': 'livox0000000001', 'use_sim_time': sim}],
        output='screen')
    model = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        parameters=[{'robot_description': ET.tostring(xml.getroot(), encoding='unicode'),
                     'use_sim_time': sim}], output='screen')
    projection = {key: robot[key] for key in (
        'min_height', 'max_height', 'range_min', 'range_max',
        'angle_min', 'angle_max', 'angle_increment', 'scan_time')}
    projection.update(target_frame='base_link', transform_tolerance=0.05,
                      use_inf=True, queue_size=10, use_sim_time=sim)
    preprocess = Node(
        package='songwei_bringup', executable='cloud_preprocessor.py',
        name='mid360_motion_compensation',
        condition=IfCondition(LaunchConfiguration('preprocess_cloud')),
        parameters=[{key: robot[key] for key in (
            'lidar_xyz', 'lidar_rpy', 'self_filter_x', 'self_filter_y')},
            {'use_sim_time': sim}],
        remappings=[('/livox/lidar', value('cloud_topic'))], output='screen')
    projection_topic = ('/songwei/cloud_deskewed' if value('preprocess_cloud').lower() == 'true'
                        else value('cloud_topic'))
    scan = Node(
        package='pointcloud_to_laserscan', executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan', parameters=[projection],
        remappings=[('cloud_in', projection_topic), ('scan', '/scan')], output='screen')
    slam = Node(
        package='slam_toolbox', executable='async_slam_toolbox_node', name='slam_toolbox',
        condition=IfCondition(LaunchConfiguration('start_slam')),
        parameters=[value('slam_config'), {'use_sim_time': sim}], output='screen')
    rviz = Node(
        package='rviz2', executable='rviz2', name='songwei_rviz',
        condition=IfCondition(LaunchConfiguration('rviz')),
        arguments=['-d', os.path.join(share, 'rviz', 'manual_mapping.rviz')],
        parameters=[{'use_sim_time': sim}], output='screen')
    critical = [base, lidar, model, preprocess, scan, slam]
    handlers = [RegisterEventHandler(OnProcessExit(
        target_action=node,
        on_exit=[EmitEvent(event=Shutdown(reason='A required mapping process exited'))]))
        for node in critical]
    return handlers + critical + [rviz]


def generate_launch_description():
    share = get_package_share_directory('songwei_bringup')
    defaults = {
        'start_base': 'true', 'start_lidar': 'true', 'rviz': 'true', 'use_sim_time': 'false',
        'start_slam': 'true',
        'cloud_topic': '/livox/lidar',
        'preprocess_cloud': 'true',
        'robot_config': os.path.join(share, 'config', 'robot.yaml'),
        'lidar_config': os.path.join(share, 'config', 'MID360_config.json'),
        'slam_config': os.path.join(share, 'config', 'slam_toolbox.yaml'),
    }
    return LaunchDescription([DeclareLaunchArgument(name, default_value=default)
                              for name, default in defaults.items()] + [OpaqueFunction(function=setup)])
