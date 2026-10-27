#!/usr/bin/env python3
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from model_constraints import O10RightModel
from retargeting import (RetargetFeatures, all_gesture_activations,
                         extract_features, fist_cross_activation,
                         gesture_activations, number_gesture_activations,
                         palm_frame, retarget)
from config_loader import load_config
from safe_controller import SafeTargetLimiter


def synthetic_hand(spread: bool = False, curled: bool = False, thumb_bent: bool = False) -> list[np.ndarray]:
    p = np.zeros((21, 3), dtype=np.float64)
    p[0] = [0.0, 0.0, 0.0]
    p[1], p[2] = [-0.30, 0.30, 0.0], [-0.62, 0.48, 0.0]
    if thumb_bent:
        p[3], p[4] = [-0.60, 0.24, 0.30], [-0.42, 0.06, 0.42]
    else:
        p[3], p[4] = [-0.94, 0.66, 0.0], [-1.25, 0.84, 0.0]
    bases = [(5, 0.42), (9, 0.12), (13, -0.16), (17, -0.42)]
    offsets = [0.28, 0.0, -0.20, -0.36] if spread else [0.03, 0.0, -0.02, -0.04]
    for (mcp, x), dx in zip(bases, offsets):
        pip, dip, tip = mcp + 1, mcp + 2, mcp + 3
        p[mcp] = [x, 1.0, 0.0]
        p[pip] = [x + dx, 1.52, 0.0]
        if curled:
            p[dip] = [x + dx, 1.52, 0.38]
            p[tip] = [x + dx, 1.22, 0.58]
        else:
            p[dip] = [x + 2 * dx, 2.02, 0.0]
            p[tip] = [x + 3 * dx, 2.48, 0.0]
    return list(p)


def main() -> int:
    model = O10RightModel.from_json(PROJECT / "config/omnihand_right_model.json")
    neutral = RetargetFeatures(
        thumb_curl=0.5, index_curl=0.2, middle_curl=0.7,
        ring_curl=0.7, pinky_curl=0.7, thumb_spread=0.5,
        thumb_cross=0.0, thumb_roll=0.25, thumb_abad=0.75,
        index_spread=0.5, ring_spread=0.5, pinky_spread=0.5)
    active = retarget(neutral, model)
    assert len(active) == 10
    assert all(limit.minimum <= value <= limit.maximum for value, limit in zip(active, model.active))
    assert set(model.passive_from_active(active)) == set(model.spec["passive_joints"])
    thumb_config = {"joint_mapping": {
        "R_thumb_abad_joint": {"invert": True},
        "R_index_abad_joint": {"invert": True},
    }}
    thumb_open = RetargetFeatures(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    thumb_opposed = RetargetFeatures(0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0)
    open_angles = retarget(thumb_open, model, thumb_config)
    opposed_angles = retarget(thumb_opposed, model, thumb_config)
    assert np.isclose(open_angles[0], model.active[0].minimum)
    assert np.isclose(open_angles[1], model.active[1].maximum)
    assert np.isclose(opposed_angles[0], model.active[0].maximum)
    assert np.isclose(opposed_angles[1], model.active[1].maximum)

    # Crossing alone (open hand) and closure alone (thumb outside) must not
    # trigger automatic fist closure.  Both together must supplement all three
    # thumb motions that are obscured in a full fist.
    cross_open = RetargetFeatures(0.1, 0.1, 0.1, 0.1, 0.1, 0, 1, 0, 0, 0, 0, 0)
    outside_fist = RetargetFeatures(0.1, 1, 1, 1, 1, 0, 0.5, 0, 0, 0, 0, 0)
    crossed_fist = RetargetFeatures(0.1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0)
    assert fist_cross_activation(cross_open) == 0
    assert fist_cross_activation(outside_fist) == 0
    assert fist_cross_activation(crossed_fist) > 0.99
    outside_angles = retarget(outside_fist, model, thumb_config)
    crossed_angles = retarget(crossed_fist, model, thumb_config)
    outside_roll = (outside_angles[0] - model.active[0].minimum) / (model.active[0].maximum - model.active[0].minimum)
    assert 0.73 < outside_roll < 0.77
    crossed_roll = (crossed_angles[0] - model.active[0].minimum) / (model.active[0].maximum - model.active[0].minimum)
    assert 0.73 < crossed_roll < 0.77
    assert crossed_angles[2] > 0.6 * model.active[2].maximum

    noisy_closed_spread = RetargetFeatures(0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1)
    gated_angles = retarget(noisy_closed_spread, model, thumb_config)
    assert np.isclose(gated_angles[3], model.active[3].maximum)
    assert np.isclose(gated_angles[6], model.active[6].minimum)
    assert np.isclose(gated_angles[8], model.active[8].minimum)

    official_config = load_config(PROJECT / "config/simulation.json", PROJECT)
    paper_features = replace(thumb_open, thumb_extension=1.0,
                             finger_parallel=1.0)
    ok_features = replace(thumb_open, index_curl=0.5,
                          thumb_index_pinch=1.0, thumb_extension=1.0)
    assert np.allclose(gesture_activations(paper_features), (1.0, 0.0))
    assert np.allclose(gesture_activations(ok_features), (0.0, 1.0))
    assert np.allclose(retarget(paper_features, model, official_config),
                       official_config["gesture_presets"]["paper"])
    assert np.allclose(retarget(ok_features, model, official_config),
                       model.clamp_active(official_config["gesture_presets"]["ok"]))

    number_patterns = {
        "num1": (0.0, 1.0, 1.0, 1.0, 0.0),
        "num2": (0.0, 0.0, 1.0, 1.0, 0.0),
        "num3": (0.0, 0.0, 0.0, 1.0, 0.0),
        "num4": (0.0, 0.0, 0.0, 0.0, 0.0),
        "num6": (1.0, 1.0, 1.0, 0.0, 1.0),
        "num8": (0.0, 1.0, 1.0, 1.0, 1.0),
    }
    for name, (index, middle, ring, pinky, thumb_extension) in number_patterns.items():
        number_features = replace(
            thumb_open, index_curl=index, middle_curl=middle,
            ring_curl=ring, pinky_curl=pinky,
            thumb_extension=thumb_extension)
        scores = number_gesture_activations(number_features)
        assert scores[name] == 1.0, (name, scores)
        assert sum(value > 0.0 for value in scores.values()) == 1, (name, scores)
        assert np.allclose(retarget(number_features, model, official_config),
                           model.clamp_active(official_config["gesture_presets"][name]))

    # Values measured from the user's NUM2 screenshot must confidently select
    # the official NUM2 thumb even though its thumb-index distance resembles a
    # pinch because the two folded fingers disqualify OK.
    captured_num2 = replace(
        thumb_open, thumb_curl=0.5279, index_curl=0.0813,
        middle_curl=0.1154, ring_curl=0.5457, pinky_curl=0.5571,
        thumb_cross=1.0, thumb_roll=0.5731, thumb_abad=1.0,
        thumb_index_pinch=1.0, thumb_extension=0.2170,
        finger_parallel=0.8283)
    captured_scores = all_gesture_activations(captured_num2)
    assert captured_scores["num2"] > 0.90, captured_scores
    assert captured_scores["ok"] == 0.0, captured_scores
    captured_target = retarget(captured_num2, model, official_config)
    official_num2 = model.clamp_active(official_config["gesture_presets"]["num2"])
    assert np.allclose(captured_target[:3], official_num2[:3], atol=0.02)

    limiter = SafeTargetLimiter(model, max_step_fraction=0.05, workspace_fraction=0.10)
    minimum = [limit.minimum for limit in model.active]
    limiter.reset(minimum, now=0.0)
    limited = limiter.update([limit.maximum for limit in model.active], now=0.1)
    assert all(abs(value - limit.minimum) <= (limit.maximum-limit.minimum)*0.05 + 1e-9
               for value, limit in zip(limited, model.active))

    together = extract_features(synthetic_hand())
    spread = extract_features(synthetic_hand(spread=True))
    assert spread.index_spread > together.index_spread + 0.25
    assert spread.ring_spread > together.ring_spread + 0.25
    assert spread.pinky_spread > together.pinky_spread + 0.25
    curled = extract_features(synthetic_hand(curled=True))
    assert curled.index_curl > together.index_curl + 0.35
    assert curled.pinky_curl > together.pinky_curl + 0.35
    bent_thumb = extract_features(synthetic_hand(thumb_bent=True))
    assert bent_thumb.thumb_curl > together.thumb_curl + 0.25

    points = np.asarray(synthetic_hand(spread=True))
    theta = 0.73
    rotation = np.array([[np.cos(theta), -np.sin(theta), 0.0],
                         [np.sin(theta), np.cos(theta), 0.0],
                         [0.0, 0.0, 1.0]])
    transformed = list((points @ rotation.T) * 2.7 + np.array([4.0, -2.0, 1.0]))
    rotated = extract_features(transformed)
    assert np.allclose(list(spread.__dict__.values()), list(rotated.__dict__.values()), atol=1e-7)
    frame = palm_frame(points)
    assert abs(float(np.dot(frame.radial, frame.longitudinal))) < 1e-10
    assert abs(float(np.dot(frame.normal, frame.longitudinal))) < 1e-10
    print("retargeting v6 official poses, fist target, spread gate and safety limiter: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
