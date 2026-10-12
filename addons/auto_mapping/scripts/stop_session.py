#!/usr/bin/env python3
"""Stop only the recorded addon launch and its verified descendants."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path(sys.argv[1])
pidfile = root / 'logs' / ('session_' + sys.argv[2] + '.pid')
if not pidfile.exists():
    print('没有本模块的启动进程记录。')
    sys.exit(0)
pid = int(pidfile.read_text().strip())
proc = Path('/proc') / str(pid)
if not proc.exists():
    print('自动建图已停止。')
    sys.exit(0)
args = (proc / 'cmdline').read_bytes().split(b'\0')
if [b'launch', b'songwei_auto_mapping', b'auto_mapping.launch.py'] != args[2:5]:
    # Python ros2 CLI has [python3, /opt/.../ros2, launch, package, filename].
    print('记录的 PID 不是本模块启动进程，不发送信号。', file=sys.stderr)
    sys.exit(1)


def process_info(target):
    try:
        fields = (Path('/proc') / str(target) / 'stat').read_text().rsplit(')', 1)[1].split()
        return int(fields[1]), fields[19], fields[0]  # parent, start time, state
    except (OSError, ValueError):
        return None


owned = {pid: process_info(pid)[1]}
for _ in range(8):
    added = False
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        child = int(path.name)
        info = process_info(child)
        if info and info[0] in owned and child not in owned:
            owned[child] = info[1]
            added = True
    if not added:
        break


def alive(target):
    info = process_info(target)
    return info and info[1] == owned[target] and info[2] != 'Z'


def send(target, sig):
    if alive(target):
        try:
            os.kill(target, sig)
        except ProcessLookupError:
            pass


try:
    subprocess.run([str(root / 'scripts/pause.sh')], timeout=30, check=False)
except subprocess.TimeoutExpired:
    print('暂停响应超时，继续关闭本模块进程。', file=sys.stderr)
send(pid, signal.SIGINT)
deadline = time.monotonic() + 20
while time.monotonic() < deadline and any(alive(p) for p in owned):
    time.sleep(.2)
for child in reversed(owned):
    send(child, signal.SIGTERM)
deadline = time.monotonic() + 5
while time.monotonic() < deadline and any(alive(p) for p in owned):
    time.sleep(.2)
remaining = [p for p in owned if alive(p)]
if remaining:
    print('仍有本模块进程未退出，请查看启动日志：' + str(remaining), file=sys.stderr)
    sys.exit(1)
pidfile.unlink(missing_ok=True)
print('自动建图模块已停止。')
