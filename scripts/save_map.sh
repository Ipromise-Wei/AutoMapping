#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
MAP_NAME="${1:-manual_$(date +%Y%m%d_%H%M%S)}"
[[ "$MAP_NAME" =~ ^[A-Za-z0-9_-]+$ ]] || { echo 'Map name: letters, digits, _ or - only.' >&2; exit 1; }
MAP_PATH="$SONGWEI_ROOT/maps/$MAP_NAME"
exec 8>"$SONGWEI_ROOT/logs/save_map.lock"
flock -n 8 || { echo '另一张地图正在保存，请稍后重试。' >&2; exit 1; }
for suffix in yaml pgm posegraph data; do
  [[ ! -e "$MAP_PATH.$suffix" ]] || { echo '同名地图文件已存在，请使用新名字。' >&2; exit 1; }
done
# Check mapping is active before saving; navigation's /map is not a new map.
/usr/bin/python3 - <<'PY'
import rclpy
from slam_toolbox.srv import SerializePoseGraph
rclpy.init()
node = rclpy.create_node('songwei_save_map_check')
client = node.create_client(SerializePoseGraph, '/slam_toolbox/serialize_map')
ready = client.wait_for_service(timeout_sec=3.0)
node.destroy_node()
rclpy.shutdown()
if not ready:
    raise SystemExit('手动建图尚未运行。请先启动 start_mapping.sh，完成采集后保持其运行再保存。')
PY
# Stage all four files together, so a failed save cannot look like a complete map.
SAVE_DIR="$(mktemp -d "$SONGWEI_ROOT/maps/.saving_${MAP_NAME}.XXXXXX")"
trap 'rm -rf -- "$SAVE_DIR"' EXIT
STAGED_PATH="$SAVE_DIR/$MAP_NAME"
ros2 run nav2_map_server map_saver_cli -f "$STAGED_PATH" --ros-args \
  -p save_map_timeout:=10.0 -p map_subscribe_transient_local:=true \
  -p free_thresh_default:=0.196 -p occupied_thresh_default:=0.65
timeout 15 ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '$STAGED_PATH'}"
for suffix in yaml pgm posegraph data; do test -s "$STAGED_PATH.$suffix"; done
for suffix in pgm posegraph data yaml; do mv -- "$STAGED_PATH.$suffix" "$MAP_PATH.$suffix"; done
echo "已保存：$MAP_PATH.yaml / .pgm / .posegraph / .data"
