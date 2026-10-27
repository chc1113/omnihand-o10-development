#!/usr/bin/env python3
"""Interactive seven-pose calibration with raw landmark recording."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from retargeting import extract_raw_features
from vision_pipeline import select_hand

POSES = [
    ("neutral", "自然张开", "掌心正对镜头，四指伸直并拢；拇指伸直向侧方张开，与手掌同一平面"),
    ("together", "四指并拢", "掌心正对镜头，四指伸直并紧；拇指保持自然，不要遮挡四指"),
    ("spread", "四指张开", "掌心正对镜头，四指伸直并尽量侧向张开；手掌不要转动"),
    ("fist", "四指握拳", "掌心正对镜头，四指完全弯曲；拇指放在拳外，不要遮住四指"),
    ("full_fist", "完整握拳", "四指完全弯曲后，将拇指自然横放在拳面；不要把拇指藏进掌心"),
    ("thumb_abducted", "拇指抬离掌面", "四指伸直并拢；拇指保持伸直，朝镜头方向抬起，离开手掌平面"),
    ("thumb_opposed", "拇指横向对掌", "四指伸直并拢；拇指尽量伸直，横向移向小指根部，不要主动弯指尖"),
    ("thumb_bent", "拇指弯曲", "四指伸直并拢；保持拇指根部方向稳定，弯曲拇指的两个可见关节"),
]

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def put_text(frame: np.ndarray, text: str, xy: tuple[int, int], size: int,
             color: tuple[int, int, int]) -> np.ndarray:
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    draw.text(xy, text, font=ImageFont.truetype(FONT, size), fill=(color[2], color[1], color[0]))
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 单视觉一键引导标定")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=2.0)
    parser.add_argument("--output", default="data/calibration_samples.jsonl")
    parser.add_argument("--poses", help="只重采指定姿态，逗号分隔；例如 full_fist 或 thumb_abducted,thumb_opposed")
    args = parser.parse_args()
    output = PROJECT / args.output if not Path(args.output).is_absolute() else Path(args.output)
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"camera {args.camera} open failed")
    selected = set(args.poses.split(",")) if args.poses else {item[0] for item in POSES}
    unknown = selected - {item[0] for item in POSES}
    if unknown:
        parser.error(f"未知姿态: {','.join(sorted(unknown))}")
    existing = []
    if args.poses and output.is_file():
        existing = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()
                    if line.strip() and json.loads(line).get("pose") not in selected]
    samples = []
    mp_hands = mp.solutions.hands
    drawer = mp.solutions.drawing_utils
    try:
        with mp_hands.Hands(static_image_mode=False, max_num_hands=2, model_complexity=0,
                            min_detection_confidence=0.65, min_tracking_confidence=0.65) as tracker:
            for pose, title, instruction in POSES:
                if pose not in selected:
                    continue
                capturing = False
                started = 0.0
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        continue
                    frame = cv2.flip(frame, 1)
                    result = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    hand = select_hand(result, "Right", 0.60)
                    if hand is not None:
                        drawer.draw_landmarks(frame, hand.drawing_landmarks, mp_hands.HAND_CONNECTIONS)
                    if capturing and hand is not None:
                        features = extract_raw_features(hand.points)
                        samples.append({"wall_time": time.time(), "pose": pose,
                                        "coordinate_source": hand.coordinate_source,
                                        "handedness_score": hand.score,
                                        "points": [point.tolist() for point in hand.points],
                                        "features": features})
                    remaining = args.seconds - (time.monotonic() - started) if capturing else args.seconds
                    frame = put_text(frame, f"姿态：{title}", (10, 8), 24, (0, 255, 255))
                    frame = put_text(frame, instruction, (10, 42), 18, (255, 255, 255))
                    state = (f"正在采集，还剩 {max(0, remaining):.1f} 秒" if capturing
                             else "姿态摆好并稳定后，按空格开始采集")
                    frame = put_text(frame, state, (10, 72), 20, (0, 255, 0))
                    cv2.imshow("O10 guided calibration", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (27, ord("q")):
                        raise KeyboardInterrupt
                    if not capturing and key == ord(" ") and hand is not None:
                        capturing, started = True, time.monotonic()
                    if capturing and remaining <= 0:
                        break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in existing + samples), encoding="utf-8")
    subprocess.run([sys.executable, str(PROJECT / "scripts/check_calibration.py"),
                    "--input", str(output)], check=True)
    subprocess.run([sys.executable, str(PROJECT / "scripts/solve_calibration.py"),
                    "--input", str(output)], check=True)
    print(f"guided calibration complete: {len(samples)} frames")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("calibration cancelled; existing profile was not changed")
        raise SystemExit(130)
