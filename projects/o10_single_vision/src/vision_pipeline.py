"""Shared MediaPipe result selection and coordinate extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class TrackedHand:
    drawing_landmarks: Any
    points: list[np.ndarray]
    label: str
    score: float
    coordinate_source: str


def select_hand(result: Any, required_label: str = "Right", min_score: float = 0.55) -> TrackedHand | None:
    landmarks = list(result.multi_hand_landmarks or [])
    handedness = list(result.multi_handedness or [])
    world = list(result.multi_hand_world_landmarks or [])
    candidates = []
    for index, drawing in enumerate(landmarks):
        label, score = "Unknown", 0.0
        if index < len(handedness) and handedness[index].classification:
            cls = handedness[index].classification[0]
            label, score = str(cls.label), float(cls.score)
        if label != required_label or score < min_score:
            continue
        source = world[index] if index < len(world) else drawing
        points = [np.array([item.x, item.y, item.z], dtype=np.float64) for item in source.landmark]
        candidates.append(TrackedHand(drawing, points, label, score,
                                      "world" if index < len(world) else "normalized"))
    return max(candidates, key=lambda item: item.score, default=None)
