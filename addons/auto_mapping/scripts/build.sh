#!/usr/bin/env bash
set -eo pipefail
AUTO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SONGWEI_ROOT="$(cd "$AUTO_ROOT/../.." && pwd)"
source "$SONGWEI_ROOT/scripts/env.sh"
mkdir -p "$AUTO_ROOT/logs"
# Prevent replacing optional libraries while an auto-mapping session is running.
exec 8>"$AUTO_ROOT/logs/module.lock"
flock -n 8 || { echo '自动建图模块正在运行或编译，请先关闭。' >&2; exit 1; }
cd "$AUTO_ROOT"
export CMAKE_BUILD_PARALLEL_LEVEL=2
colcon --log-base log build --base-paths src --build-base build --install-base install \
  --symlink-install --parallel-workers 2 \
  --packages-select frontier_exploration_ros2 songwei_auto_mapping \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
