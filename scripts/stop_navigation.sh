#!/usr/bin/env bash
set -eo pipefail
SONGWEI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$SONGWEI_ROOT/logs/navigation.pid"
[[ -f "$PID_FILE" ]] || { echo '没有 V2 导航进程记录。'; exit 0; }
NAV_PID="$(cat "$PID_FILE")"
[[ "$NAV_PID" =~ ^[0-9]+$ ]] || { echo '无效 PID。' >&2; exit 1; }
if [[ ! -r "/proc/$NAV_PID/cmdline" ]]; then echo '导航已停止。'; exit 0; fi
COMMAND="$(tr '\0' ' ' < "/proc/$NAV_PID/cmdline")"
[[ "$COMMAND" == *'ros2 launch songwei_bringup navigation.launch.py'* ]] || {
  echo 'PID 已被其他进程占用，不发送信号。' >&2; exit 1;
}
source "$SONGWEI_ROOT/scripts/env.sh"
timeout 3 ros2 service call /navigate_to_pose/_action/cancel_goal action_msgs/srv/CancelGoal '{}' >/dev/null 2>&1 || true
timeout 3 ros2 topic pub --once /songwei/cmd_vel geometry_msgs/msg/Twist '{}' >/dev/null 2>&1 || true
mapfile -t CHILDREN < <(pgrep -P "$NAV_PID" || true)
if (( ${#CHILDREN[@]} )); then kill -INT "${CHILDREN[@]}" 2>/dev/null || true; fi
kill -INT "$NAV_PID" 2>/dev/null || true
for _ in {1..15}; do
  if ! kill -0 "$NAV_PID" 2>/dev/null; then echo 'V2 导航已停止。'; exit 0; fi
  sleep 1
done
kill -TERM "$NAV_PID" 2>/dev/null || true
echo '关闭仍在进行，请查看导航启动终端。' >&2
exit 1
