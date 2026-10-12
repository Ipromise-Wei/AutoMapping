#!/usr/bin/env python3
"""Resolve and validate a saved ROS map before navigation starts hardware."""
import math
from pathlib import Path
import sys

import yaml
from PIL import Image


def resolve_map(argument):
    root = Path(__file__).resolve().parent.parent
    candidate = Path(argument).expanduser()
    if not candidate.is_absolute() and len(candidate.parts) == 1 and not candidate.is_file():
        candidate = root / 'maps' / candidate
    if not candidate.suffix:
        candidate = candidate.with_suffix('.yaml')
    path = candidate.resolve()
    if path.suffix.lower() not in ('.yaml', '.yml'):
        raise ValueError('请选择地图 YAML 文件；图片文件本身不包含地图比例和坐标原点。')
    if not path.is_file():
        raise ValueError(f'地图 YAML 不存在：{path}')
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('地图 YAML 内容必须是字段映射。')
    image_name = data.get('image')
    if not isinstance(image_name, str) or not image_name:
        raise ValueError('地图 YAML 缺少有效的 image 字段。')
    image_path = Path(image_name)
    if not image_path.is_absolute():
        image_path = path.parent / image_path
    if not image_path.is_file():
        raise ValueError(f'地图图片不存在：{image_path}')
    with Image.open(image_path) as image:
        image.verify()
    resolution = float(data['resolution'])
    if not math.isfinite(resolution) or not math.isclose(resolution, 0.05, abs_tol=1e-8):
        raise ValueError(f'当前导航轨迹库要求地图分辨率为 0.05 m/像素，实际为 {resolution}。')
    origin = data['origin']
    if not isinstance(origin, list) or len(origin) != 3 or not all(math.isfinite(float(v)) for v in origin):
        raise ValueError('origin 必须包含有效的 [x, y, yaw]。')
    if abs(float(origin[2])) > 1e-8:
        raise ValueError('当前二维代价地图要求 origin 的 yaw 为 0。')
    free, occupied = float(data['free_thresh']), float(data['occupied_thresh'])
    if not 0.0 <= free < occupied <= 1.0:
        raise ValueError('阈值必须满足 0 ≤ free_thresh < occupied_thresh ≤ 1。')
    if data.get('negate') not in (0, 1):
        raise ValueError('negate 必须为 0 或 1。')
    if data.get('mode', 'trinary') not in ('trinary', 'scale', 'raw'):
        raise ValueError('mode 必须为 trinary、scale 或 raw。')
    return path


if __name__ == '__main__':
    try:
        print(resolve_map(sys.argv[1] if len(sys.argv) > 1 else 'room_401'))
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as error:
        print(f'地图检查失败：{error}', file=sys.stderr)
        sys.exit(1)
