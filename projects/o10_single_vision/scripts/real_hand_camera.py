#!/usr/bin/env python3
"""Guarded camera-to-O10 USB control.

Motion requires both --arm REAL_HAND and pressing A in the camera window.
Q/Escape or loss of tracking immediately stops further command writes.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from config_loader import load_config
from model_constraints import O10RightModel
from o10_hardware import O10UsbHand
from retargeting import extract_features, retarget
from safe_controller import SafeTargetLimiter
from vision_pipeline import select_hand


def resolve_port(configured: str) -> str:
    if configured != "auto":
        return configured
    matches = sorted(glob.glob("/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_*-if00"))
    if matches:
        return matches[0]
    if Path("/dev/ttyACM0").exists():
        return "/dev/ttyACM0"
    raise RuntimeError("O10 USB CDC port not found")


def smooth(previous: list[float] | None, current: list[float], alpha: float) -> list[float]:
    if previous is None:
        return list(current)
    return [alpha * new + (1.0 - alpha) * old for old, new in zip(previous, current)]


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 单视觉真机控制（安全限制版）")
    parser.add_argument("--config", default=str(PROJECT / "config/hardware.json"))
    parser.add_argument("--arm", default="", help="必须明确填写 REAL_HAND 才允许写命令")
    parser.add_argument("--probe-only", action="store_true", help="只连接并回读，不打开摄像头、不写命令")
    args = parser.parse_args()
    config = load_config(args.config, PROJECT)
    model = O10RightModel.from_json(PROJECT / config["model_config"])
    port = resolve_port(str(config.get("port", "auto")))
    hand = O10UsbHand(port, int(config.get("device_id", 1)))
    measured = hand.read_angles()
    errors = hand.read_errors()
    print(f"CONNECTED {port}")
    print(hand.vendor_summary())
    print("measured radians:", ", ".join(f"{x:.4f}" for x in measured))
    if errors:
        raise RuntimeError("hardware reports errors; motion blocked: " + "; ".join(errors))
    if args.probe_only:
        print("READ-ONLY PROBE OK; no command was sent")
        return 0
    if bool(config.get("require_calibration", True)) and "calibration_loaded_from" not in config:
        raise RuntimeError("motion blocked: run guided calibration first; config/calibration_right.json is missing")
    if bool(config.get("require_calibration", True)) and int(config.get("calibration_version", 0)) < 4:
        raise RuntimeError("motion blocked: calibration profile predates fist geometry; run solve_calibration.py")
    if "gesture_presets_loaded_from" not in config:
        raise RuntimeError("motion blocked: official PAPER/OK gesture profile is missing")
    if args.arm != "REAL_HAND":
        raise RuntimeError("motion blocked: rerun with --arm REAL_HAND")

    limiter = SafeTargetLimiter(
        model,
        max_step_fraction=float(config.get("max_step_fraction", 0.01)),
        workspace_fraction=float(config.get("workspace_fraction", 0.08)),
        velocity_scale=float(config.get("velocity_scale", 1.0)),
    )
    limiter.reset(measured)
    cap = cv2.VideoCapture(int(config.get("camera_index", 0)))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(config.get("camera_width", 640)))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(config.get("camera_height", 480)))
    if not cap.isOpened():
        raise RuntimeError("camera open failed")

    mp_hands = mp.solutions.hands
    drawer = mp.solutions.drawing_utils
    enabled = False
    valid_frames = 0
    filtered: list[float] | None = None
    last_seen = 0.0
    last_write = 0.0
    last_read = 0.0
    log_path = PROJECT / config.get("log_path", "logs/real_hand_session.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_stream = log_path.open("a", encoding="utf-8")
    try:
        with mp_hands.Hands(static_image_mode=False, max_num_hands=2, model_complexity=0,
                            min_detection_confidence=0.65, min_tracking_confidence=0.65) as tracker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                result = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                tracked = select_hand(result, config.get("required_hand", "Right"),
                                      float(config.get("min_handedness_score", 0.65)))
                now = time.monotonic()
                if tracked is not None:
                    last_seen = now
                    valid_frames += 1
                    features = extract_features(tracked.points, config)
                    target = retarget(features, model, config)
                    filtered = smooth(filtered, target, float(config.get("smooth_alpha", 0.20)))
                    drawer.draw_landmarks(frame, tracked.drawing_landmarks, mp_hands.HAND_CONNECTIONS)
                else:
                    valid_frames = 0

                stale = now - last_seen > float(config.get("lost_hand_timeout_s", 0.25))
                ready = valid_frames >= int(config.get("valid_frames_to_arm", 12))
                if stale:
                    enabled = False
                if enabled and ready and filtered is not None and now - last_write >= 1.0 / float(config.get("control_hz", 10)):
                    command = limiter.update(filtered, now)
                    hand.write_angles(command)
                    log_stream.write(json.dumps({"wall_time": time.time(), "command": command,
                                                 "measured": measured, "tracking_score": tracked.score},
                                                ensure_ascii=False) + "\n")
                    log_stream.flush()
                    last_write = now
                if now - last_read >= 1.0 / float(config.get("readback_hz", 2)):
                    measured = hand.read_angles()
                    last_read = now

                state = "ENABLED" if enabled else ("READY - PRESS A" if ready else "TRACKING NOT READY")
                color = (0, 0, 255) if enabled else (0, 220, 255)
                cv2.putText(frame, state, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(frame, "Q/ESC stop, SPACE pause; full range, 30 Hz", (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)
                cv2.imshow("O10 REAL HAND guarded control", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
                if key == ord(" "):
                    enabled = False
                if key == ord("a") and ready and not stale:
                    enabled = True
    finally:
        log_stream.close()
        cap.release()
        cv2.destroyAllWindows()
        print("STOPPED: no further O10 commands will be sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
