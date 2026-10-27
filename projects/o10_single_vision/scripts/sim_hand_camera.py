#!/usr/bin/env python3
"""Camera-driven MuJoCo simulation of the O10 right hand.

The only output is a virtual hand pose. This script never imports OmniHand,
never opens a serial device, and never sends a command to real hardware.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import mediapipe as mp
import mujoco

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from model_constraints import O10RightModel
from retargeting import (all_gesture_activations, extract_features,
                         fist_cross_activation, retarget)
from config_loader import load_config
from vision_pipeline import select_hand


def build_model_xml(asset_path: Path, hand_path: Path) -> str:
    """Merge the package's asset and hand fragments into one valid MJCF."""
    asset_root = ET.parse(asset_path).getroot()
    hand_root = ET.parse(hand_path).getroot()
    root = ET.Element("mujoco", {"model": "omnihand_right_camera_sim"})
    compiler = asset_root.find("compiler")
    if compiler is not None:
        compiler = ET.fromstring(ET.tostring(compiler, encoding="unicode"))
        meshdir = (asset_path.parent / "../meshes").resolve()
        compiler.set("meshdir", str(meshdir))
        root.append(compiler)
    for tag in ("asset", "default"):
        element = asset_root.find(tag)
        if element is not None:
            root.append(ET.fromstring(ET.tostring(element, encoding="unicode")))
    for tag in ("worldbody", "contact", "actuator", "equality"):
        element = hand_root.find(tag)
        if element is not None:
            root.append(ET.fromstring(ET.tostring(element, encoding="unicode")))
    return ET.tostring(root, encoding="unicode")


def set_qpos(model: mujoco.MjModel, data: mujoco.MjData, joints: dict[str, float]) -> None:
    for name, value in joints.items():
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if joint_id < 0:
            raise RuntimeError(f"MuJoCo joint not found: {name}")
        data.qpos[model.jnt_qposadr[joint_id]] = value
    mujoco.mj_forward(model, data)


def initial_pose(model_spec: O10RightModel, mode: str) -> list[float]:
    if mode == "minimum":
        return [joint.minimum for joint in model_spec.active]
    if mode == "maximum":
        return [joint.maximum for joint in model_spec.active]
    return [(joint.minimum + joint.maximum) * 0.5 for joint in model_spec.active]


def smooth(previous: list[float] | None, current: list[float], alpha: float) -> list[float]:
    if previous is None:
        return list(current)
    alpha = max(0.0, min(1.0, alpha))
    return [alpha * new + (1.0 - alpha) * old for old, new in zip(previous, current)]


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 摄像头到 MuJoCo 虚拟手仿真")
    parser.add_argument("--config", default=str(PROJECT / "config/simulation.json"))
    parser.add_argument("--camera", type=int, help="临时覆盖 camera_index")
    parser.add_argument("--no-camera", action="store_true", help="仅打开静态虚拟手")
    args = parser.parse_args()

    config = load_config(args.config, PROJECT)
    model_spec = O10RightModel.from_json(PROJECT / config["model_config"])
    asset_path = Path(config["source_asset"])
    hand_path = Path(config["source_mjcf"])
    if not asset_path.is_file() or not hand_path.is_file():
        raise RuntimeError(f"模型资源不存在: {asset_path} / {hand_path}")
    xml = build_model_xml(asset_path, hand_path)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    active = initial_pose(model_spec, config.get("start_pose", "midpoint"))
    set_qpos(model, data, model_spec.all_joints(active))

    cap = None
    if not args.no_camera:
        camera_index = config["camera_index"] if args.camera is None else args.camera
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config["camera_width"])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config["camera_height"])
        if not cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 index={camera_index}")

    try:
        from mujoco import viewer as mujoco_viewer
        with mujoco_viewer.launch_passive(model, data) as viewer:
            tracker_api = mp.solutions.hands
            drawer = mp.solutions.drawing_utils
            last_frame = time.monotonic()
            last_control = 0.0
            fps = 0.0
            tracker_context = (tracker_api.Hands(
                static_image_mode=False, max_num_hands=2, model_complexity=0,
                min_detection_confidence=0.6, min_tracking_confidence=0.6)
                if cap is not None else nullcontext(None))
            with tracker_context as tracker:
                filtered_active: list[float] | None = None
                while viewer.is_running():
                    if cap is not None:
                        ok, frame = cap.read()
                        if ok:
                            frame = cv2.flip(frame, 1)
                            result = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                            hand = select_hand(result, config.get("required_hand", "Right"),
                                               float(config.get("min_handedness_score", 0.55)))
                            if hand is not None:
                                features = extract_features(hand.points, config)
                                target = retarget(features, model_spec, config)
                                now = time.monotonic()
                                if now - last_control >= 1.0 / float(config.get("control_hz", 30)):
                                    filtered_active = smooth(filtered_active, target, float(config.get("smooth_alpha", 0.25)))
                                    set_qpos(model, data, model_spec.all_joints(filtered_active))
                                    last_control = now
                                drawer.draw_landmarks(frame, hand.drawing_landmarks, tracker_api.HAND_CONNECTIONS)
                                cv2.putText(frame, "SIMULATION ONLY", (10, 28),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 0), 2)
                                cross_activation = fist_cross_activation(features)
                                gestures = all_gesture_activations(features)
                                gesture_name, gesture_score = max(
                                    gestures.items(), key=lambda item: item[1])
                                active_by_name = dict(zip(model_spec.active_names, filtered_active or target))
                                limits_by_name = {item.name: item for item in model_spec.active}
                                def joint_norm(name: str) -> float:
                                    limit = limits_by_name[name]
                                    return ((active_by_name[name] - limit.minimum) /
                                            (limit.maximum - limit.minimum))
                                cv2.putText(frame, f"{hand.label} {hand.score:.2f} {hand.coordinate_source}",
                                            (10, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
                                cv2.putText(frame, f"gesture {gesture_name.upper()} {gesture_score:.2f}  FIST {cross_activation:.2f}",
                                            (10, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
                                cv2.putText(frame, "thumb model R/A/C " + "/".join(
                                            f"{joint_norm(name):.2f}" for name in
                                            ("R_thumb_roll_joint", "R_thumb_abad_joint",
                                             "R_thumb_mcp_joint")),
                                            (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
                                cv2.putText(frame, f"finger curl I/M/R/P {features.index_curl:.2f}/{features.middle_curl:.2f}/{features.ring_curl:.2f}/{features.pinky_curl:.2f}",
                                            (10, 142), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
                                cv2.putText(frame, "O10 flex rad I/M/R/P " + "/".join(
                                            f"{active_by_name[name]:.2f}" for name in
                                            ("R_index_pip_joint", "R_middle_pip_joint",
                                             "R_ring_pip_joint", "R_pinky_pip_joint")),
                                            (10, 164), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
                                cv2.putText(frame, "O10 spread rad I/R/P " + "/".join(
                                            f"{active_by_name[name]:.2f}" for name in
                                            ("R_index_abad_joint", "R_ring_abad_joint",
                                             "R_pinky_abad_joint")),
                                            (10, 186), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
                            else:
                                cv2.putText(frame, "NO_HAND - virtual hand holds pose", (10, 28),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                            now = time.monotonic()
                            instant = 1.0 / max(now - last_frame, 1e-6)
                            fps = instant if fps == 0 else 0.15 * instant + 0.85 * fps
                            last_frame = now
                            cv2.putText(frame, f"camera FPS {fps:.1f}", (10, 52),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                            cv2.imshow("O10 camera input (simulation only)", frame)
                            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                                break
                    viewer.sync()
                    time.sleep(float(config.get("viewer_sync_seconds", 0.01)))
    finally:
        if cap is not None:
            cap.release()
            cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
