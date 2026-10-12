#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
exec 9>"$SONGWEI_ROOT/logs/mapping.lock"
flock -n 9 || { echo '建图或导航仍在运行，请先用对应的停止脚本关闭。' >&2; exit 1; }
# Hardware access remains exclusive even when ROS_DOMAIN_ID differs.
matches="$(pgrep -af '^(/[^ ]*/)?(ranger_base_node|livox_ros_driver2_node|async_slam_toolbox_node|fastlio_mapping|controller_server|map_server|amcl|explore)( |$)' || true)"
if [[ -n "$matches" ]]; then
  echo '已有底盘/雷达/建图或导航程序，请在其启动终端 Ctrl+C 后再启动 V2。' >&2
  echo "$matches" >&2
  exit 1
fi
CAN_DEVICE="$(/usr/bin/python3 -c 'import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))["can_device"])' "$SONGWEI_ROOT/src/songwei_bringup/config/robot.yaml")"
ip -details link show "$CAN_DEVICE" | grep -q 'bitrate 500000' || {
  echo "CAN 未配置为 500000，请先运行 scripts/setup_can.sh $CAN_DEVICE" >&2; exit 1;
}
ip link show "$CAN_DEVICE" | grep -q 'UP' || { echo 'CAN interface is down.' >&2; exit 1; }
if [[ -z "${DISPLAY:-}" ]]; then
  export DISPLAY=:0
  export XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
fi
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID; 手动建图；键盘控制独立命令话题 /songwei/cmd_vel"
echo $$ > "$SONGWEI_ROOT/logs/manual_mapping.pid"
exec ros2 launch songwei_bringup manual_mapping.launch.py "$@"
