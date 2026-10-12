import os
from nav2_common.launch import RewrittenYaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler, EmitEvent
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node


def setup(context):
    share = get_package_share_directory('songwei_bringup')
    def value(name):
        return LaunchConfiguration(name).perform(context)
    sim = value('use_sim_time').lower() == 'true'
    common = {'use_sim_time': sim}
    configured_params = RewrittenYaml(source_file=value('params_file'), root_key='',
        param_rewrites={'use_sim_time': value('use_sim_time'), 'yaml_filename': value('map'),
            'default_nav_to_pose_bt_xml': os.path.join(share, 'config', 'navigate_to_pose.xml'),
            'default_nav_through_poses_bt_xml': os.path.join(share, 'config', 'navigate_through_poses.xml'),
            'lattice_filepath': os.path.join(get_package_share_directory('nav2_smac_planner'),
                'sample_primitives', '5cm_resolution', '0.5m_turning_radius', 'diff', 'output.json')},
        convert_types=True)

    # Keep the sensor include's rviz=false local so navigation retains its own switch.
    sensors = GroupAction(scoped=True, actions=[IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'manual_mapping.launch.py')),
        launch_arguments={'start_base': value('start_base'), 'start_lidar': value('start_lidar'),
            'rviz': 'false', 'start_slam': 'false', 'use_sim_time': value('use_sim_time')}.items())])
    def server(package, executable, name, remaps=None):
        # Keep nested costmap settings in the complete parameter dictionary.
        return Node(package=package, executable=executable, name=name,
            parameters=[configured_params, common], remappings=remaps or [], output='screen')
    map_server = server('nav2_map_server', 'map_server', 'map_server')
    amcl = server('nav2_amcl', 'amcl', 'amcl')
    controller = server('nav2_controller', 'controller_server', 'controller_server',
                        [('cmd_vel', '/songwei/nav_cmd_vel')])
    planner = server('nav2_planner', 'planner_server', 'planner_server')
    behavior = server('nav2_behaviors', 'behavior_server', 'behavior_server',
                      [('cmd_vel', '/songwei/nav_cmd_vel')])
    navigator = server('nav2_bt_navigator', 'bt_navigator', 'bt_navigator')
    smoother = server('nav2_velocity_smoother', 'velocity_smoother', 'velocity_smoother',
                      [('cmd_vel', '/songwei/nav_cmd_vel'), ('cmd_vel_smoothed', '/songwei/cmd_vel')])
    localization_manager = Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_localization', parameters=[common, {'autostart': True,
        'node_names': ['map_server', 'amcl'], 'bond_timeout': 4.0}], output='screen')
    navigation_manager = Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_navigation', parameters=[common, {'autostart': True,
        'node_names': ['controller_server', 'planner_server', 'behavior_server',
                       'bt_navigator', 'velocity_smoother'], 'bond_timeout': 4.0}], output='screen')
    rviz = Node(package='rviz2', executable='rviz2', name='songwei_rviz',
        condition=IfCondition(LaunchConfiguration('rviz')), parameters=[common],
        arguments=['-d', os.path.join(share, 'rviz', 'navigation.rviz')], output='screen')
    critical = [map_server, amcl, controller, planner, behavior, navigator,
                smoother, localization_manager, navigation_manager]
    handlers = [RegisterEventHandler(OnProcessExit(target_action=node,
        on_exit=[EmitEvent(event=Shutdown(reason='A required navigation process exited'))]))
        for node in critical]
    return handlers + [sensors] + critical + [rviz]


def generate_launch_description():
    share = get_package_share_directory('songwei_bringup')
    defaults = {'map': '/home/hzauaiot/songwei_V2.0/maps/room_401.yaml',
        'params_file': os.path.join(share, 'config', 'navigation.yaml'),
        'start_base': 'true', 'start_lidar': 'true', 'rviz': 'true', 'use_sim_time': 'false'}
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v) for k,v in defaults.items()]
                             + [OpaqueFunction(function=setup)])
