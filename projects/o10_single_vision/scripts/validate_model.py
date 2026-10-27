#!/usr/bin/env python3
"""Validate the local model metadata against the O10 SDK's ten-joint order."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from model_constraints import O10RightModel


def main() -> int:
    model = O10RightModel.from_json(PROJECT / "config/omnihand_right_model.json")
    source = Path(model.spec["source_root"])
    mjcf = source / model.spec["mjcf"]
    urdf = source / model.spec["urdf"]
    if not mjcf.is_file() or not urdf.is_file():
        raise SystemExit(f"模型文件不存在: {mjcf} / {urdf}")
    text = mjcf.read_text(encoding="utf-8")
    actuator_joints = re.findall(r'<position\s+name="[^"]+"\s+joint="([^"]+)"', text)
    if tuple(actuator_joints) != model.active_names:
        raise SystemExit(f"MJCF actuator 顺序不一致: {actuator_joints}")
    urdf_text = urdf.read_text(encoding="utf-8")
    missing = [name for name in model.active_names if f'name="{name}"' not in urdf_text]
    if missing:
        raise SystemExit(f"URDF 缺少主动关节: {missing}")
    sample = model.all_joints([limit.minimum for limit in model.active])
    upper = model.all_joints([limit.maximum for limit in model.active])
    print(json.dumps({
        "model": model.spec["model_name"],
        "active_joint_count": len(model.active),
        "active_joint_order": model.active_names,
        "passive_at_min": sample,
        "passive_at_max": upper,
        "status": "ok",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

