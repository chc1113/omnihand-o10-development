#!/usr/bin/env python3
"""Render O10 joint min/mid/max poses from two views for direction audits."""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import cv2
import mujoco
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from config_loader import load_config
from model_constraints import O10RightModel


def build_model_xml(asset_path: Path, hand_path: Path) -> str:
    asset_root = ET.parse(asset_path).getroot()
    hand_root = ET.parse(hand_path).getroot()
    root = ET.Element("mujoco", {"model": "omnihand_joint_sweep"})
    compiler = ET.fromstring(ET.tostring(asset_root.find("compiler"), encoding="unicode"))
    compiler.set("meshdir", str((asset_path.parent / "../meshes").resolve()))
    root.append(compiler)
    for tag in ("asset", "default"):
        root.append(ET.fromstring(ET.tostring(asset_root.find(tag), encoding="unicode")))
    for tag in ("worldbody", "contact", "actuator", "equality"):
        root.append(ET.fromstring(ET.tostring(hand_root.find(tag), encoding="unicode")))
    return ET.tostring(root, encoding="unicode")


def set_pose(model: mujoco.MjModel, data: mujoco.MjData,
             model_spec: O10RightModel, active: list[float]) -> None:
    for name, value in model_spec.all_joints(active).items():
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        data.qpos[model.jnt_qposadr[joint_id]] = value
    mujoco.mj_forward(model, data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/joint_sweep.png")
    args = parser.parse_args()
    cfg = load_config(PROJECT / "config/simulation.json", PROJECT)
    spec = O10RightModel.from_json(PROJECT / cfg["model_config"])
    model = mujoco.MjModel.from_xml_string(build_model_xml(Path(cfg["source_asset"]),
                                                            Path(cfg["source_mjcf"])))
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=280, width=280)
    rest = [joint.minimum for joint in spec.active]
    # Ab/adduction rest values are the mechanical neutral positions for this
    # right-hand model, not uniformly the numeric minima.
    for name in ("R_thumb_abad_joint", "R_index_abad_joint"):
        index = spec.active_names.index(name)
        rest[index] = spec.active[index].maximum

    audited = (
        "R_thumb_roll_joint", "R_thumb_abad_joint", "R_thumb_mcp_joint",
        "R_index_pip_joint", "R_middle_pip_joint",
        "R_ring_pip_joint", "R_pinky_pip_joint",
    )
    cameras = ((90.0, -12.0, "palm"), (0.0, -12.0, "side"))
    cells: list[np.ndarray] = []
    for joint_name in audited:
        joint_index = spec.active_names.index(joint_name)
        limit = spec.active[joint_index]
        row = []
        for azimuth, elevation, view_name in cameras:
            for fraction, value_name in ((0.0, "min"), (0.5, "mid"), (1.0, "max")):
                active = list(rest)
                active[joint_index] = limit.minimum + fraction * (limit.maximum - limit.minimum)
                set_pose(model, data, spec, active)
                camera = mujoco.MjvCamera()
                camera.type = mujoco.mjtCamera.mjCAMERA_FREE
                camera.lookat[:] = (0.0, 0.1, 0.08)
                camera.distance = 0.28
                camera.azimuth = azimuth
                camera.elevation = elevation
                renderer.update_scene(data, camera)
                image = cv2.cvtColor(renderer.render(), cv2.COLOR_RGB2BGR)
                cv2.putText(image, f"{view_name} {value_name} {active[joint_index]:+.2f}",
                            (7, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 220, 255), 1,
                            cv2.LINE_AA)
                row.append(image)
        strip = np.hstack(row)
        cv2.putText(strip, joint_name, (7, strip.shape[0] - 9),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1, cv2.LINE_AA)
        cells.append(strip)
    result = np.vstack(cells)
    output = PROJECT / args.output if not Path(args.output).is_absolute() else Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), result):
        raise RuntimeError(f"failed to write {output}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
