#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
[[ $# -eq 0 || ( $# -eq 1 && "$1" == '--paused' ) ]] || {
  echo '用法：start.sh [--paused]（默认准备完成后自动探索）' >&2; exit 1;
}
AUTO_START=true
[[ "${1:-}" != '--paused' ]] || AUTO_START=false
mkdir -p "$AUTO_ROOT/logs"
exec 8>"$AUTO_ROOT/logs/module.lock"
flock -n 8 || { echo '自动建图模块正在运行或编译。' >&2; exit 1; }
# This is the SAME lock used by the untouched original entrypoints.
exec 9>"$SONGWEI_ROOT/logs/mapping.lock"
flock -n 9 || { echo '手动建图或导航仍在运行，请先用原有停止脚本关闭。' >&2; exit 1; }
matches="$(pgrep -af '^(/[^ ]*/)?(ranger_base_node|livox_ros_driver2_node|async_slam_toolbox_node|fastlio_mapping|controller_server|map_server|amcl|explore|frontier_explorer)( |$)' || true)"
[[ -z "$matches" ]] || { echo '已有底盘、雷达、建图或导航进程，请先关闭：' >&2; echo "$matches" >&2; exit 1; }
CAN_DEVICE="$(/usr/bin/python3 -c 'import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))["can_device"])' "$SONGWEI_ROOT/src/songwei_bringup/config/robot.yaml")"
ip -details link show "$CAN_DEVICE" | grep -q 'bitrate 500000' || {
  echo "CAN 未就绪，请先运行原项目 scripts/setup_can.sh $CAN_DEVICE" >&2; exit 1;
}
ip link show "$CAN_DEVICE" | grep -q 'UP' || { echo 'CAN interface is down.' >&2; exit 1; }
if [[ -z "${DISPLAY:-}" ]]; then
  export DISPLAY=:0
  export XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
fi
echo "独立自动建图；ROS_DOMAIN_ID=$ROS_DOMAIN_ID；自动探索=$AUTO_START"
echo '从空白地图开始。请将遥控器切换到 CAN 控制模式。自动探索启用后车辆将自行行驶。'
echo '暂停：addons/auto_mapping/scripts/pause.sh；保存：addons/auto_mapping/scripts/save_map.sh 新地图名'
echo $$ > "$AUTO_ROOT/logs/session_${ROS_DOMAIN_ID}.pid"
exec ros2 launch songwei_auto_mapping auto_mapping.launch.py autostart:="$AUTO_START"
