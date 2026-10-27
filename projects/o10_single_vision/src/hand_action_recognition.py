"""Real-time, vision-only hand action recognition.

This module intentionally has no OmniHand SDK dependency and cannot send
commands to the O10. It is the perception baseline for the single-vision
project.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class HandFeatures:
    bends: list[float]
    pinch_distance: float
    handedness: str


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    denominator = float(np.linalg.norm(ba) * np.linalg.norm(bc))
    if denominator < 1e-8:
        return 180.0
    cosine = float(np.dot(ba, bc) / denominator)
    return math.degrees(math.acos(clamp(cosine, -1.0, 1.0)))


def bend(points: list[np.ndarray], mcp: int, pip: int, tip: int) -> float:
    """Return an approximate straight-to-curled value in [0, 1]."""
    return clamp((180.0 - joint_angle(points[mcp], points[pip], points[tip])) / 125.0, 0.0, 1.0)


def extract_features(points: list[np.ndarray], handedness: str) -> HandFeatures:
    bends = [
        bend(points, 2, 3, 4),
        bend(points, 5, 6, 8),
        bend(points, 9, 10, 12),
        bend(points, 13, 14, 16),
        bend(points, 17, 18, 20),
    ]
    palm_size = float(np.linalg.norm(points[9] - points[0])) + 1e-8
    pinch_distance = float(np.linalg.norm(points[4] - points[8])) / palm_size
    return HandFeatures(bends=bends, pinch_distance=pinch_distance, handedness=handedness)


def classify(features: HandFeatures, config: dict) -> str:
    thumb, index, middle, ring, little = features.bends
    if features.pinch_distance <= config["pinch_max_normalized_distance"]:
        return "PINCH"
    if index <= config["point_index_max_bend"] and all(
        value >= config["point_other_min_bend"] for value in (middle, ring, little)
    ):
        return "POINT"
    if all(value <= config["open_max_bend"] for value in (index, middle, ring, little)):
        return "OPEN"
    if all(value >= config["fist_min_bend"] for value in (index, middle, ring, little)):
        return "FIST"
    return "HAND"


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def append_event(log_path: Path, action: str, features: HandFeatures | None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "wall_time": time.time(),
        "action": action,
        "handedness": features.handedness if features else None,
        "bends": features.bends if features else None,
        "pinch_distance": features.pinch_distance if features else None,
    }
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 单视觉手部动作识别（无真机控制）")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config/vision.json"))
    parser.add_argument("--camera", type=int, help="临时覆盖 camera_index")
    parser.add_argument("--no-log", action="store_true", help="不写动作变化日志")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    camera_index = config["camera_index"] if args.camera is None else args.camera
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config["height"])
    cap.set(cv2.CAP_PROP_FPS, config["fps"])
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 index={camera_index}")

    log_path = resolve_path(config["log_path"])
    history: deque[str] = deque(maxlen=max(1, int(config["gesture_confirm_frames"])))
    stable_action = "NO_HAND"
    last_logged_action: str | None = None
    last_frame_time = time.monotonic()
    fps_value = 0.0

    mp_hands = mp.solutions.hands
    drawer = mp.solutions.drawing_utils

    try:
        with mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config["max_num_hands"],
            model_complexity=config["model_complexity"],
            min_detection_confidence=config["min_detection_confidence"],
            min_tracking_confidence=config["min_tracking_confidence"],
        ) as tracker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue

                frame = cv2.flip(frame, 1)
                result = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                features: HandFeatures | None = None
                candidate = "NO_HAND"

                if result.multi_hand_landmarks:
                    landmarks = result.multi_hand_landmarks[0]
                    label = "Unknown"
                    if result.multi_handedness:
                        label = result.multi_handedness[0].classification[0].label
                    points = [np.array([p.x, p.y, p.z], dtype=np.float64) for p in landmarks.landmark]
                    features = extract_features(points, label)
                    candidate = classify(features, config)
                    drawer.draw_landmarks(frame, landmarks, mp_hands.HAND_CONNECTIONS)

                history.append(candidate)
                if len(history) == history.maxlen and len(set(history)) == 1:
                    stable_action = history[0]

                if stable_action != last_logged_action:
                    if not args.no_log:
                        append_event(log_path, stable_action, features)
                    last_logged_action = stable_action

                now = time.monotonic()
                instant_fps = 1.0 / max(now - last_frame_time, 1e-6)
                fps_value = instant_fps if fps_value == 0.0 else 0.15 * instant_fps + 0.85 * fps_value
                last_frame_time = now

                color = (0, 200, 0) if stable_action != "NO_HAND" else (0, 0, 255)
                cv2.putText(frame, f"VISION ONLY  {stable_action}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
                cv2.putText(frame, f"FPS {fps_value:.1f}  camera {camera_index}", (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
                if features:
                    bends_text = ",".join(f"{value:.2f}" for value in features.bends)
                    cv2.putText(frame, f"{features.handedness} bends [{bends_text}]", (12, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                    cv2.putText(frame, f"pinch {features.pinch_distance:.2f}", (12, 106), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

                cv2.imshow("O10 single vision - hand actions", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

