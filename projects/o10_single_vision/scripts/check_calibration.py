#!/usr/bin/env python3
"""Audit calibration semantics before using the profile for hardware."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from retargeting import extract_raw_features


def current_features(row: dict) -> dict[str, float]:
    if "points" not in row:
        raise ValueError("calibration row has no raw landmarks; recapture calibration")
    return extract_raw_features(row["points"])


def median(rows: list[dict], name: str) -> float:
    return statistics.median(float(current_features(row)[name]) for row in rows)


def spread(rows: list[dict], name: str) -> float:
    values = [float(current_features(row)[name]) for row in rows]
    return max(values) - min(values)


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 O10 单视觉标定姿态是否可分离")
    parser.add_argument("--input", default="data/calibration_samples.jsonl")
    args = parser.parse_args()
    source = PROJECT / args.input if not Path(args.input).is_absolute() else Path(args.input)
    groups: dict[str, list[dict]] = defaultdict(list)
    with source.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                item = json.loads(line)
                groups[item["pose"]].append(item)

    warnings: list[str] = []
    required = ("neutral", "together", "spread", "fist", "thumb_abducted", "thumb_opposed", "thumb_bent")
    for pose in required:
        if len(groups[pose]) < 20:
            warnings.append(f"{pose}: only {len(groups[pose])} frames; recapture")
    scores = [float(row.get("handedness_score", 0.0)) for rows in groups.values() for row in rows]
    if scores and min(scores) < 0.80:
        warnings.append(f"handedness score minimum is {min(scores):.3f}; low-confidence frames exist")

    cross_pair = ("fist", "full_fist", 0.18) if groups.get("full_fist") else ("neutral", "thumb_opposed", 0.30)
    pairs = {
        "index_spread": ("together", "spread", 0.10),
        "ring_spread": ("together", "spread", 0.10),
        "pinky_spread": ("together", "spread", 0.10),
        "thumb_roll": ("neutral", "thumb_abducted", 0.20),
        "thumb_abad": ("neutral", "thumb_opposed", 0.20),
        "thumb_curl": ("neutral", "thumb_bent", 0.20),
        "thumb_cross": cross_pair,
        "index_curl": ("neutral", "fist", 0.30),
        "middle_curl": ("neutral", "fist", 0.30),
        "ring_curl": ("neutral", "fist", 0.30),
        "pinky_curl": ("neutral", "fist", 0.30),
    }
    print("pose counts:", {key: len(groups[key]) for key in required})
    for feature, (low_pose, high_pose, threshold) in pairs.items():
        if not groups[low_pose] or not groups[high_pose]:
            continue
        low = median(groups[low_pose], feature)
        high = median(groups[high_pose], feature)
        delta = abs(high - low)
        print(f"{feature:14s} {low_pose:16s}={low:+.4f}  {high_pose:16s}={high:+.4f}  separation={delta:.4f}")
        if delta < threshold:
            warnings.append(f"{feature}: separation {delta:.4f} < {threshold:.2f}; recapture these two poses")

    advisories: list[str] = []
    # Opposition naturally includes some flexion, but excessive hidden curl
    # makes the direction anchor harder for a human to reproduce.
    if groups["thumb_opposed"] and groups["neutral"]:
        opposed_curl = median(groups["thumb_opposed"], "thumb_curl")
        neutral_curl = median(groups["neutral"], "thumb_curl")
        if opposed_curl - neutral_curl > 0.15:
            advisories.append("thumb_opposed includes thumb bending; next capture should keep both thumb joints straighter")

    print("\nstatus:", "WARN" if warnings else "OK")
    for warning in warnings:
        print("-", warning)
    for advisory in advisories:
        print("- advisory:", advisory)
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
