#!/usr/bin/env bash
set -eo pipefail
CAN_DEVICE="${1:-can0}"
if pgrep -f '^/[^ ]*/ranger_base_node( |$)' >/dev/null; then
  echo '底盘驱动仍在运行，请先关闭再重新配置 CAN。' >&2; exit 1
fi
sudo modprobe gs_usb
sudo ip link set "$CAN_DEVICE" down
sudo ip link set "$CAN_DEVICE" type can bitrate 500000 restart-ms 100
sudo ip link set "$CAN_DEVICE" up
ip -details link show "$CAN_DEVICE"
