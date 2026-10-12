#!/usr/bin/env bash
set -eo pipefail
SONGWEI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
cd "$SONGWEI_ROOT"
# Prepare the official ROS2 manifest without the upstream build.sh's deletion
# of the complete workspace build and install directories.
cp src/livox_ros_driver2/package_ROS2.xml src/livox_ros_driver2/package.xml
mkdir -p src/livox_ros_driver2/launch
cp -a src/livox_ros_driver2/launch_ROS2/. src/livox_ros_driver2/launch/
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
colcon build --symlink-install --parallel-workers 2 \
  --allow-overriding nav2_regulated_pure_pursuit_controller \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  -DROS_EDITION=ROS2 -DDISTRO_ROS=humble
