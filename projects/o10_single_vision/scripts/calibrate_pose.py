#!/usr/bin/env python3
"""Record MediaPipe feature samples for later per-user calibration."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from retargeting import extract_raw_features
from vision_pipeline import select_hand


def main() -> int:
    parser = argparse.ArgumentParser(description="采集单视觉重定向标定姿态")
    parser.add_argument("pose", choices=("neutral", "fist", "spread", "together",
                                         "thumb_abducted", "thumb_opposed", "thumb_bent"))
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--output", default="data/calibration_samples.jsonl")
    args = parser.parse_args()
    output = PROJECT / args.output if not Path(args.output).is_absolute() else Path(args.output)
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 index={args.camera}")
    tracker_api = mp.solutions.hands
    samples = []
    start = time.monotonic()
    try:
        with tracker_api.Hands(static_image_mode=False, max_num_hands=2, model_complexity=0,
                               min_detection_confidence=0.6, min_tracking_confidence=0.6) as tracker:
            while time.monotonic() - start < args.seconds:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                result = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                hand = select_hand(result, "Right", 0.55)
                if hand is not None:
                    features = extract_raw_features(hand.points)
                    samples.append({"wall_time": time.time(), "pose": args.pose,
                                    "coordinate_source": hand.coordinate_source,
                                    "handedness_score": hand.score,
                                    "points": [point.tolist() for point in hand.points],
                                    "features": features})
                cv2.putText(frame, f"CALIBRATE {args.pose}  {max(0.0, args.seconds - (time.monotonic()-start)):.1f}s",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("O10 calibration", frame)
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        for sample in samples:
            stream.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"saved {len(samples)} samples to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
