#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
(( $# <= 1 )) || { echo '用法：start_navigation.sh [地图名或 YAML 路径]' >&2; exit 1; }
MAP_FILE="$(/usr/bin/python3 "$SONGWEI_ROOT/scripts/resolve_map.py" "${1:-room_401}")"
# Share the hardware lock with manual mapping.
exec 9>"$SONGWEI_ROOT/logs/mapping.lock"
flock -n 9 || { echo '建图或导航仍在运行，请先关闭后再启动导航。' >&2; exit 1; }
matches="$(pgrep -af '^(/[^ ]*/)?(ranger_base_node|livox_ros_driver2_node|async_slam_toolbox_node|fastlio_mapping|controller_server|map_server|amcl|explore)( |$)' || true)"
if [[ -n "$matches" ]]; then
  echo '已有底盘、雷达、地图或导航进程，请先关闭：' >&2
  echo "$matches" >&2; exit 1
fi
CAN_DEVICE="$(/usr/bin/python3 -c 'import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))["can_device"])' "$SONGWEI_ROOT/src/songwei_bringup/config/robot.yaml")"
ip -details link show "$CAN_DEVICE" | grep -q 'bitrate 500000' || {
  echo "CAN 未就绪，请运行 scripts/setup_can.sh $CAN_DEVICE" >&2; exit 1;
}
ip link show "$CAN_DEVICE" | grep -q 'UP' || { echo 'CAN interface is down.' >&2; exit 1; }
if [[ -z "${DISPLAY:-}" ]]; then
  export DISPLAY=:0
  export XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
fi
echo "导航地图：$MAP_FILE；ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo '先用 2D Pose Estimate 指定车的位置和朝向，再用 2D Goal Pose 指定目标。'
echo '导航需将遥控器切换到允许 CAN 控制的模式。默认速度上限 0.15 m/s。'
echo $$ > "$SONGWEI_ROOT/logs/navigation.pid"
exec ros2 launch songwei_bringup navigation.launch.py map:="$MAP_FILE"
