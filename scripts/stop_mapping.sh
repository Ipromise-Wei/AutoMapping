#!/usr/bin/env bash
set -eo pipefail
SONGWEI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$SONGWEI_ROOT/logs/manual_mapping.pid"
[[ -f "$PID_FILE" ]] || { echo '没有 V2 启动进程记录。'; exit 0; }
MAPPING_PID="$(cat "$PID_FILE")"
[[ "$MAPPING_PID" =~ ^[0-9]+$ ]] || { echo '无效 PID。' >&2; exit 1; }
if [[ ! -r "/proc/$MAPPING_PID/cmdline" ]]; then
  echo 'V2 已停止。'; exit 0
fi
COMMAND="$(tr '\0' ' ' < "/proc/$MAPPING_PID/cmdline")"
[[ "$COMMAND" == *'ros2 launch songwei_bringup manual_mapping.launch.py'* ]] || {
  echo 'PID 已被其他进程占用，不发送信号。' >&2; exit 1;
}
# Background ROS launch may inherit an ignored SIGINT. Stop its known child
# nodes first so a terminated launcher cannot leave hardware drivers orphaned.
mapfile -t MAPPING_CHILDREN < <(pgrep -P "$MAPPING_PID" || true)
if (( ${#MAPPING_CHILDREN[@]} )); then
  kill -INT "${MAPPING_CHILDREN[@]}" 2>/dev/null || true
fi
kill -INT "$MAPPING_PID" 2>/dev/null || true
for _ in {1..15}; do
  if ! kill -0 "$MAPPING_PID" 2>/dev/null; then
    echo 'V2 手动建图已停止。'; exit 0
  fi
  sleep 1
done
kill -TERM "$MAPPING_PID" 2>/dev/null || true
echo '关闭仍在进行，请查看建图启动终端。' >&2
exit 1
