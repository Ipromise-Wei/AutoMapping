"""Optional SLAM + Nav2 + frontier stack; original bringup files are read-only."""
import os
from ament_index_python.packages import get_package_share_directory
from nav2_common.launch import RewrittenYaml
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction, IncludeLaunchDescription,
                            OpaqueFunction, RegisterEventHandler, EmitEvent)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node


def setup(context):
    share = get_package_share_directory('songwei_auto_mapping')
    original = get_package_share_directory('songwei_bringup')
    def value(name):
        return LaunchConfiguration(name).perform(context)
    common = {'use_sim_time': value('use_sim_time').lower() == 'true'}
    params = RewrittenYaml(source_file=value('params_file'), root_key='',
        param_rewrites={'use_sim_time': value('use_sim_time'),
            'default_nav_to_pose_bt_xml': os.path.join(share, 'config', 'navigate_to_pose.xml'),
            'default_nav_through_poses_bt_xml': os.path.join(share, 'config', 'navigate_through_poses.xml'),
            'lattice_filepath': os.path.join(get_package_share_directory('nav2_smac_planner'),
                'sample_primitives', '5cm_resolution', '0.5m_turning_radius', 'diff', 'output.json')},
        convert_types=True)
    sensors_and_slam = GroupAction(scoped=True, actions=[IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(original, 'launch', 'manual_mapping.launch.py')),
        launch_arguments={'start_base': value('start_base'), 'start_lidar': value('start_lidar'),
            'rviz': 'false', 'start_slam': 'true', 'use_sim_time': value('use_sim_time')}.items())])
    def server(package, executable, remaps=None):
        return Node(package=package, executable=executable, name=executable,
                    parameters=[params, common], remappings=remaps or [], output='screen')
    controller = server('nav2_controller', 'controller_server', [('cmd_vel', '/songwei/nav_cmd_vel')])
    planner = server('nav2_planner', 'planner_server')
    behavior = server('nav2_behaviors', 'behavior_server', [('cmd_vel', '/songwei/nav_cmd_vel')])
    navigator = server('nav2_bt_navigator', 'bt_navigator')
    smoother = server('nav2_velocity_smoother', 'velocity_smoother',
        [('cmd_vel', '/songwei/nav_cmd_vel'), ('cmd_vel_smoothed', '/songwei/cmd_vel')])
    manager = Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_auto_mapping', parameters=[common, {'autostart': True,
        'node_names': ['controller_server', 'planner_server', 'behavior_server',
                       'bt_navigator', 'velocity_smoother'], 'bond_timeout': 4.0}], output='screen')
    explorer = Node(package='frontier_exploration_ros2', executable='frontier_explorer',
        name='frontier_explorer', namespace='auto_mapping',
        parameters=[value('exploration_params'), common, {'autostart': False}],
        # Upstream publishes its frontier/selected-goal visualization only at DEBUG.
        arguments=['--ros-args', '--log-level', 'auto_mapping.frontier_explorer:=debug'],
        output='screen')
    gate = Node(package='songwei_auto_mapping', executable='exploration_control.py',
        name='auto_mapping_start_gate', arguments=['start'], parameters=[common],
        condition=IfCondition(LaunchConfiguration('autostart')), output='screen')
    def gate_exit(event, context):
        if event.returncode:
            return [EmitEvent(event=Shutdown(reason='Auto mapping readiness/start failed'))]
        return []
    critical = [controller, planner, behavior, navigator, smoother, manager, explorer]
    handlers = [RegisterEventHandler(OnProcessExit(target_action=node,
        on_exit=[EmitEvent(event=Shutdown(reason='A required auto mapping process exited'))]))
        for node in critical]
    rviz = Node(package='rviz2', executable='rviz2', name='auto_mapping_rviz',
        condition=IfCondition(LaunchConfiguration('rviz')), parameters=[common],
        arguments=['-d', os.path.join(share, 'rviz', 'auto_mapping.rviz')], output='screen')
    return handlers + [RegisterEventHandler(OnProcessExit(target_action=gate, on_exit=gate_exit)),
                       sensors_and_slam] + critical + [rviz, gate]


def generate_launch_description():
    share = get_package_share_directory('songwei_auto_mapping')
    defaults = {'start_base': 'true', 'start_lidar': 'true', 'rviz': 'true',
        'use_sim_time': 'false', 'autostart': 'true',
        'params_file': os.path.join(share, 'config', 'navigation.yaml'),
        'exploration_params': os.path.join(share, 'config', 'exploration.yaml')}
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v) for k, v in defaults.items()]
                             + [OpaqueFunction(function=setup)])
