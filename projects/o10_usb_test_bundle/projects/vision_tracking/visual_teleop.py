"""O10 camera-to-hand demo.

The default mode is dry-run: it draws the landmarks and prints the target
angles without sending commands. Pass --live only after USB communication and
the mapping have been checked on an unladen hand.
"""

from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass
from typing import Iterable

import cv2
import mediapipe as mp
import numpy as np


@dataclass(frozen=True)
class JointLimit:
    low: float
    high: float


RIGHT_LIMITS = (
    JointLimit(-0.03, 1.12), JointLimit(-1.64, 0.05), JointLimit(0.00, 0.84),
    JointLimit(-0.16, 0.00), JointLimit(0.00, 1.48), JointLimit(0.00, 1.48),
    JointLimit(0.00, 0.17), JointLimit(0.00, 1.48), JointLimit(0.00, 0.19),
    JointLimit(0.00, 1.48),
)
LEFT_LIMITS = (
    JointLimit(-1.12, 0.03), JointLimit(-0.05, 1.64), JointLimit(-0.84, 0.00),
    JointLimit(0.00, 0.16), JointLimit(0.00, 1.48), JointLimit(0.00, 1.48),
    JointLimit(-0.17, 0.00), JointLimit(0.00, 1.48), JointLimit(-0.19, 0.00),
    JointLimit(0.00, 1.48),
)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle ABC in degrees."""
    ba = a - b
    bc = c - b
    denominator = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denominator < 1e-8:
        return 180.0
    cosine = float(np.dot(ba, bc) / denominator)
    return math.degrees(math.acos(clamp(cosine, -1.0, 1.0)))


def bend(points: list[np.ndarray], mcp: int, pip: int, tip: int) -> float:
    """Map an approximately straight-to-curled finger to [0, 1]."""
    # 180 degrees is straight; about 55 degrees is a curled finger.
    return clamp((180.0 - angle(points[mcp], points[pip], points[tip])) / 125.0, 0.0, 1.0)


def spread(points: list[np.ndarray], mcp: int, neighbour: int) -> float:
    """A camera-independent-ish lateral spread estimate in [0, 1]."""
    palm = np.linalg.norm(points[9] - points[0]) + 1e-8
    return clamp(abs(float(points[mcp][0] - points[neighbour][0])) / (0.75 * palm), 0.0, 1.0)


def retarget(points: list[np.ndarray], hand: str) -> list[float]:
    """Convert 21 MediaPipe landmarks to O10's 10 active joint angles."""
    limits = LEFT_LIMITS if hand == "left" else RIGHT_LIMITS
    thumb_bend = bend(points, 2, 3, 4)
    index_bend = bend(points, 5, 6, 8)
    middle_bend = bend(points, 9, 10, 12)
    ring_bend = bend(points, 13, 14, 16)
    pinky_bend = bend(points, 17, 18, 20)

    # Abduction estimates are deliberately conservative. They provide useful
    # open/close motion, while calibration can later replace these heuristics.
    thumb_spread = spread(points, 2, 5)
    index_spread = spread(points, 5, 9)
    ring_spread = spread(points, 13, 9)
    pinky_spread = spread(points, 17, 13)

    normalized = [
        0.25 + 0.50 * thumb_spread,
        0.25 + 0.50 * (1.0 - thumb_spread),
        thumb_bend,
        index_spread,
        index_bend,
        middle_bend,
        ring_spread,
        ring_bend,
        pinky_spread,
        pinky_bend,
    ]
    result: list[float] = []
    for value, joint_limit in zip(normalized, limits):
        # The first two and abduction joints have asymmetric ranges. Mapping
        # through the range keeps every command inside the O10 limits.
        result.append(joint_limit.low + clamp(value, 0.0, 1.0) * (joint_limit.high - joint_limit.low))
    return result


class LowPass:
    def __init__(self, alpha: float = 0.35) -> None:
        self.alpha = alpha
        self.value: np.ndarray | None = None

    def update(self, values: Iterable[float]) -> list[float]:
        current = np.asarray(list(values), dtype=np.float64)
        if self.value is None:
            self.value = current
        else:
            self.value = self.alpha * current + (1.0 - self.alpha) * self.value
        return self.value.tolist()


def create_hand(hand_name: str, port: str):
    from omnihand import HandType, OmniHand2025

    hand_type = HandType.LEFT if hand_name == "left" else HandType.RIGHT
    hand = OmniHand2025.create_hand_by_usb(
        hand_type=hand_type,
        hand_device_id=OmniHand2025.kDefaultHandDeviceId,
        uart_port=port,
        baudrate=460800,
    )
    hand.set_request_interval(100)
    hand.set_frame_recv_timeout(500)
    if not hand.init():
        raise RuntimeError(f"O10 USB 初始化失败: {port}")
    return hand


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 本机摄像头视觉追踪")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--live", action="store_true", help="发送命令到真机；默认只 dry-run")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 index={args.camera}")

    hand = create_hand(args.hand, args.port) if args.live else None
    smoother = LowPass()
    mp_hands = mp.solutions.hands
    drawer = mp.solutions.drawing_utils
    last_send = 0.0

    try:
        with mp_hands.Hands(
            static_image_mode=False, max_num_hands=1,
            model_complexity=0, min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        ) as tracker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                result = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                target: list[float] | None = None
                if result.multi_hand_landmarks:
                    landmarks = result.multi_hand_landmarks[0]
                    points = [np.array([p.x, p.y, p.z], dtype=np.float64) for p in landmarks.landmark]
                    target = smoother.update(retarget(points, args.hand))
                    drawer.draw_landmarks(frame, landmarks, mp_hands.HAND_CONNECTIONS)
                    if hand is not None and time.monotonic() - last_send >= 0.10:
                        hand.set_all_active_joint_angles(target)
                        last_send = time.monotonic()
                    cv2.putText(frame, "LIVE" if hand else "DRY-RUN", (12, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 180, 0), 2)
                    cv2.putText(frame, "angles=" + ",".join(f"{x:.2f}" for x in target),
                                (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
                else:
                    cv2.putText(frame, "hand not detected - no command", (12, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

                cv2.imshow("O10 visual tracking", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
