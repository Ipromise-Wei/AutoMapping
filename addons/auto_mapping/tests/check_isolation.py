#!/usr/bin/env python3
"""Read-only launch inspection and original-file checks; no ROS processes started."""
import hashlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch
from launch import LaunchDescription, LaunchService
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch_ros.actions import Node

root = Path(__file__).resolve().parents[1]
project = root.parents[1]
baseline = json.loads((root/'logs/original_files_before.json').read_text())
changed = [name for name, digest in baseline.items()
           if not (project/name).is_file() or hashlib.sha256((project/name).read_bytes()).hexdigest() != digest]
assert not changed, changed


def inspect(path, arguments):
    selected = []
    def record(node, context):
        def expand(value):
            return perform_substitutions(context, normalize_to_list_of_substitutions(value))
        selected.append((expand(node.node_package), expand(node.node_executable)))
    service = LaunchService()
    service.include_launch_description(LaunchDescription([IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(path)), launch_arguments=arguments.items())]))
    with patch.object(Node, 'execute', record):
        assert service.run() == 0
    return selected


own = root/'src/songwei_auto_mapping/launch/auto_mapping.launch.py'
original = project/'src/songwei_bringup/launch'
cases = []
for path, arguments, slam, amcl, hardware, rviz, explorer, gate in [
    (own, {}, 1, 0, 2, 1, 1, 1),
    (own, {'start_base':'false','start_lidar':'false','rviz':'false','autostart':'false'}, 1, 0, 0, 0, 1, 0),
    (original/'manual_mapping.launch.py', {}, 1, 0, 2, 1, 0, 0),
    (original/'navigation.launch.py', {}, 0, 1, 2, 1, 0, 0),
]:
    nodes = inspect(path, arguments)
    assert sum(p == 'slam_toolbox' for p,e in nodes) == slam, nodes
    assert sum(p == 'nav2_amcl' for p,e in nodes) == amcl, nodes
    assert sum(p == 'nav2_map_server' for p,e in nodes) == amcl, nodes
    assert sum(p in ('ranger_base','livox_ros_driver2') for p,e in nodes) == hardware, nodes
    assert sum(p == 'rviz2' for p,e in nodes) == rviz, nodes
    assert sum(p == 'frontier_exploration_ros2' for p,e in nodes) == explorer, nodes
    assert sum(e == 'exploration_control.py' for p,e in nodes) == gate, nodes
    cases.append({'launch':str(path),'args':arguments,'nodes':nodes})
packages = subprocess.check_output(['colcon','list','--names-only'], cwd=project, text=True).splitlines()
assert 'frontier_exploration_ros2' not in packages and 'songwei_auto_mapping' not in packages, packages
for script in (root/'scripts').glob('*.sh'):
    subprocess.run(['bash','-n',str(script)],check=True)
report = {'passed':True,'original_files_unchanged':len(baseline),'root_colcon_packages':packages,
          'no_ROS_processes_started':True,'cases':cases}
(root/'logs/isolation_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
