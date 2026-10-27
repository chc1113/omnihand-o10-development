#!/usr/bin/env python3
"""Build feature ranges from guided per-user calibration samples."""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(PROJECT / "src"))
from retargeting import extract_raw_features


def robust_range(low_values: list[float], high_values: list[float]) -> dict[str, float]:
    if len(low_values) < 5 or len(high_values) < 5:
        raise ValueError("each required pose needs at least five valid frames")
    low_center = float(np.median(low_values))
    high_center = float(np.median(high_values))
    inverted = high_center < low_center
    lower, upper = sorted((low_center, high_center))
    span = upper - lower
    if span < 1e-3:
        raise ValueError("pose separation is too small; recapture calibration")
    margin = 0.08 * span
    return {"low": lower - margin, "high": upper + margin,
            "invert": inverted}


def main() -> int:
    parser = argparse.ArgumentParser(description="求解单视觉个人标定参数")
    parser.add_argument("--input", default="data/calibration_samples.jsonl")
    parser.add_argument("--output", default="config/calibration_right.json")
    args = parser.parse_args()
    source = PROJECT / args.input if not Path(args.input).is_absolute() else Path(args.input)
    target = PROJECT / args.output if not Path(args.output).is_absolute() else Path(args.output)
    grouped: dict[str, list[dict]] = defaultdict(list)
    with source.open("r", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            # Always solve with the current geometry algorithm.  Raw landmarks
            # make old captures reusable after a feature implementation update.
            if "points" not in item:
                raise ValueError("calibration row has no raw landmarks; recapture calibration")
            grouped[item["pose"]].append(extract_raw_features(item["points"]))

    def values(pose: str, feature: str) -> list[float]:
        return [float(item[feature]) for item in grouped[pose]]

    cross_pair = ("fist", "full_fist") if grouped.get("full_fist") else ("neutral", "thumb_opposed")
    pairs = {
        "thumb_curl": ("neutral", "thumb_bent"),
        "index_curl": ("neutral", "fist"),
        "middle_curl": ("neutral", "fist"),
        "ring_curl": ("neutral", "fist"),
        "pinky_curl": ("neutral", "fist"),
        "index_spread": ("together", "spread"),
        "ring_spread": ("together", "spread"),
        "pinky_spread": ("together", "spread"),
        # These are different anatomical motions and must not share anchors.
        # roll: thumb leaves the palm plane; abad: thumb sweeps across the palm.
        "thumb_roll": ("neutral", "thumb_abducted"),
        "thumb_abad": ("neutral", "thumb_opposed"),
        # A dedicated complete fist is the best anchor.  Older seven-pose
        # captures remain usable through the opposition fallback.
        "thumb_cross": cross_pair,
    }
    ranges = {feature: robust_range(values(low_pose, feature), values(high_pose, feature))
              for feature, (low_pose, high_pose) in pairs.items()}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "version": 4,
        "feature_algorithm": "thumb_fist_target_and_curl_gated_spread",
        "generated_wall_time": time.time(),
        "anchor_pairs": {feature: {"low_pose": pair[0], "high_pose": pair[1]}
                         for feature, pair in pairs.items()},
        "feature_ranges": ranges,
    }, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"calibration written: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
