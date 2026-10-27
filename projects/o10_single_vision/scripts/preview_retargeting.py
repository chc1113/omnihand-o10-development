#!/usr/bin/env python3
"""Camera preview of continuous retargeting; never opens O10 hardware."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import mediapipe as mp

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from model_constraints import O10RightModel
from retargeting import extract_features, fist_cross_activation, retarget
from config_loader import load_config
from vision_pipeline import select_hand


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 连续重定向预览（无真机控制）")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--model", default=str(PROJECT / "config/omnihand_right_model.json"))
    parser.add_argument("--config", default=str(PROJECT / "config/vision.json"))
    args = parser.parse_args()
    model = O10RightModel.from_json(args.model)
    config = load_config(args.config, PROJECT)
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 index={args.camera}")
    mp_hands = mp.solutions.hands
    drawer = mp.solutions.drawing_utils
    try:
        with mp_hands.Hands(static_image_mode=False, max_num_hands=2, model_complexity=0,
                            min_detection_confidence=0.6, min_tracking_confidence=0.6) as tracker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                result = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                text = "NO_HAND"
                hand = select_hand(result, config.get("required_hand", "Right"),
                                   float(config.get("min_handedness_score", 0.55)))
                if hand is not None:
                    features = extract_features(hand.points, config)
                    active = retarget(features, model, config)
                    passive = model.passive_from_active(active)
                    drawer.draw_landmarks(frame, hand.drawing_landmarks, mp_hands.HAND_CONNECTIONS)
                    text = "active " + ",".join(f"{value:.2f}" for value in active)
                    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 0), 1)
                    cv2.putText(frame, "passive " + ",".join(f"{value:.2f}" for value in passive.values()),
                                (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 255), 1)
                    cv2.putText(frame, f"curl I/M/R/P {features.index_curl:.2f}/{features.middle_curl:.2f}/{features.ring_curl:.2f}/{features.pinky_curl:.2f}  thumb cross/fist {features.thumb_cross:.2f}/{fist_cross_activation(features):.2f}",
                                (10, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 255), 1)
                else:
                    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, "MODEL RETARGET PREVIEW - NO O10 COMMAND", (10, 98),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imshow("O10 retargeting preview", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
