#!/usr/bin/env python3
"""Verify checked-in right-hand pose targets against the official O10 SDK."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]


def main() -> int:
    from omnihand import OmniHand2025Gesture, OmniHand2025Solver

    profile = json.loads((PROJECT / "config/official_gestures_right.json").read_text(
        encoding="utf-8"))
    solver = OmniHand2025Solver(False)  # false means right hand in official SDK
    gestures = {
        "paper": OmniHand2025Gesture.OMNIHAND_2025_GESTURE_PAPER,
        "ok": OmniHand2025Gesture.OMNIHAND_2025_GESTURE_OK,
        "num1": OmniHand2025Gesture.OMNIHAND_2025_GESTURE_NUM1,
        "num2": OmniHand2025Gesture.OMNIHAND_2025_GESTURE_NUM2,
        "num3": OmniHand2025Gesture.OMNIHAND_2025_GESTURE_NUM3,
        "num4": OmniHand2025Gesture.OMNIHAND_2025_GESTURE_NUM4,
        "num6": OmniHand2025Gesture.OMNIHAND_2025_GESTURE_NUM6,
        "num8": OmniHand2025Gesture.OMNIHAND_2025_GESTURE_NUM8,
    }
    for name, gesture in gestures.items():
        actuator_input = solver.set_hand_gesture(gesture)
        actual = solver.actuator_input_to_active_joint_pos(actuator_input)
        expected = profile["active_joint_angles"][name]
        if not np.allclose(actual, expected, atol=1e-5):
            raise RuntimeError(f"official {name} changed: {list(actual)} != {expected}")
        print(f"{name}: " + ", ".join(f"{value:+.6f}" for value in actual))
    print("official O10 PAPER/OK/NUM1/NUM2/NUM3/NUM4/NUM6/NUM8 verification: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
