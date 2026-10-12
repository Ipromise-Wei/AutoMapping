#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
echo '键盘控制：i 前进，, 后退，j/l 旋转，J/L 左右横移，k/空格停止。'
echo '初始平移 0.15m/s，转速 0.25rad/s。0.3s 无按键输入自动发零速度。'
exec /usr/bin/python3 "$SONGWEI_ROOT/scripts/keyboard.py"
