#!/usr/bin/env bash
set -eo pipefail
AUTO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SONGWEI_ROOT="$(cd "$AUTO_ROOT/../.." && pwd)"
source "$SONGWEI_ROOT/scripts/env.sh"
[[ -f "$AUTO_ROOT/install/local_setup.bash" ]] || {
  echo '自动建图模块尚未编译，请先执行 addons/auto_mapping/scripts/build.sh。' >&2; return 1;
}
source "$AUTO_ROOT/install/local_setup.bash"
