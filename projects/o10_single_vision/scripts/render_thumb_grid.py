#!/usr/bin/env python3
"""Render thumb roll/opposition combinations over a closed O10 fist."""

from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import cv2
import mujoco
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "scripts"))
from config_loader import load_config
from model_constraints import O10RightModel
from render_joint_sweep import build_model_xml, set_pose


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--azimuth", type=float, default=0.0)
    parser.add_argument("--output", default="data/thumb_fist_grid.png")
    parser.add_argument("--thumb-mcp", type=float, default=0.54)
    args = parser.parse_args()
    cfg = load_config(PROJECT / "config/simulation.json", PROJECT)
    spec = O10RightModel.from_json(PROJECT / cfg["model_config"])
    model = mujoco.MjModel.from_xml_string(build_model_xml(Path(cfg["source_asset"]),
                                                            Path(cfg["source_mjcf"])))
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=260, width=260)
    by_name = {joint.name: index for index, joint in enumerate(spec.active)}
    active = [joint.minimum for joint in spec.active]
    active[by_name["R_index_abad_joint"]] = spec.active[by_name["R_index_abad_joint"]].maximum
    for name in ("R_index_pip_joint", "R_middle_pip_joint",
                 "R_ring_pip_joint", "R_pinky_pip_joint"):
        active[by_name[name]] = 1.30
    active[by_name["R_thumb_mcp_joint"]] = args.thumb_mcp

    levels = (0.0, 0.25, 0.5, 0.75, 1.0)
    rows = []
    for roll_norm in levels:
        row = []
        for abad_feature in levels:
            pose = list(active)
            roll = spec.active[by_name["R_thumb_roll_joint"]]
            abad = spec.active[by_name["R_thumb_abad_joint"]]
            pose[by_name[roll.name]] = roll.minimum + roll_norm * (roll.maximum - roll.minimum)
            # Runtime mapping inverts this normalized feature.
            pose[by_name[abad.name]] = abad.maximum - abad_feature * (abad.maximum - abad.minimum)
            set_pose(model, data, spec, pose)
            camera = mujoco.MjvCamera()
            camera.type = mujoco.mjtCamera.mjCAMERA_FREE
            camera.lookat[:] = (0.0, 0.1, 0.08)
            camera.distance = 0.28
            camera.azimuth = args.azimuth
            camera.elevation = -12.0
            renderer.update_scene(data, camera)
            image = cv2.cvtColor(renderer.render(), cv2.COLOR_RGB2BGR)
            cv2.putText(image, f"R={roll_norm:.2f} A={abad_feature:.2f}", (7, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.47, (20, 220, 255), 1, cv2.LINE_AA)
            row.append(image)
        rows.append(np.hstack(row))
    output = PROJECT / args.output
    cv2.imwrite(str(output), np.vstack(rows))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
