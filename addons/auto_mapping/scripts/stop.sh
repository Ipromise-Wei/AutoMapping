#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
exec /usr/bin/python3 "$AUTO_ROOT/scripts/stop_session.py" "$AUTO_ROOT" "$ROS_DOMAIN_ID"
