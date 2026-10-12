#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
[[ $# -eq 1 && "$1" =~ ^[A-Za-z0-9_-]+$ ]] || {
  echo '用法：save_map.sh 新地图名（字母、数字、下划线或短横线）' >&2; exit 1;
}
for suffix in yaml pgm posegraph data; do
  [[ ! -e "$SONGWEI_ROOT/maps/$1.$suffix" ]] || { echo '同名地图已存在，请换新名字。' >&2; exit 1; }
done
"$AUTO_ROOT/scripts/pause.sh"
"$SONGWEI_ROOT/scripts/save_map.sh" "$1"
echo '地图保存完成，自动探索保持暂停；继续请运行 addons/auto_mapping/scripts/resume.sh。'
