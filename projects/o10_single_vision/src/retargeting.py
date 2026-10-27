"""MediaPipe hand geometry to O10 right-hand active joints.

Version 6 recognizes the official O10 PAPER, OK, and number poses as hand
contexts, while retaining continuous landmark retargeting between them.  All
public features are normalized to [0, 1].
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping, Sequence

import numpy as np

from model_constraints import O10RightModel


@dataclass(frozen=True)
class RetargetFeatures:
    thumb_curl: float
    index_curl: float
    middle_curl: float
    ring_curl: float
    pinky_curl: float
    thumb_spread: float
    thumb_cross: float
    thumb_roll: float
    thumb_abad: float
    index_spread: float
    ring_spread: float
    pinky_spread: float
    thumb_index_pinch: float = 0.0
    thumb_extension: float = 0.0
    finger_parallel: float = 0.0


@dataclass(frozen=True)
class PalmFrame:
    radial: np.ndarray
    longitudinal: np.ndarray
    normal: np.ndarray
    scale: float


DEFAULT_FEATURE_RANGES: dict[str, tuple[float, float]] = {
    "thumb_roll": (-0.65, 0.65),
    "thumb_abad": (-0.35, 1.15),
    "thumb_curl": (0.04, 0.82),
    "index_curl": (0.03, 0.92),
    "middle_curl": (0.03, 0.92),
    "ring_curl": (0.03, 0.92),
    "pinky_curl": (0.03, 0.92),
    "index_spread": (0.02, 0.32),
    "ring_spread": (0.02, 0.27),
    "pinky_spread": (0.06, 0.48),
    "thumb_spread": (0.35, 1.15),
    # Signed thumb-tip radial position relative to the middle MCP.  More
    # positive means that the thumb has travelled farther across the palm.
    "thumb_cross": (-0.75, 0.05),
    "thumb_index_pinch": (0.0, 1.0),
    "thumb_extension": (0.0, 1.0),
    "finger_parallel": (0.0, 1.0),
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        raise ValueError("normalization range must be increasing")
    return clamp((float(value) - low) / (high - low))


def _unit(vector: np.ndarray, label: str) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    if not np.isfinite(length) or length < 1e-8:
        raise ValueError(f"degenerate hand geometry: {label}")
    return vector / length


def _points_array(points: Sequence[np.ndarray]) -> np.ndarray:
    array = np.asarray(points, dtype=np.float64)
    if array.shape != (21, 3):
        raise ValueError(f"expected 21x3 landmarks, got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError("landmarks contain NaN or infinity")
    return array


def palm_frame(points: Sequence[np.ndarray]) -> PalmFrame:
    p = _points_array(points)
    radial = _unit(p[5] - p[17], "index-pinky palm width")
    longitudinal_seed = p[9] - p[0]
    longitudinal_seed -= radial * float(np.dot(longitudinal_seed, radial))
    longitudinal = _unit(longitudinal_seed, "wrist-middle palm length")
    normal = _unit(np.cross(radial, longitudinal), "palm normal")
    scale = 0.5 * (float(np.linalg.norm(p[5] - p[17])) + float(np.linalg.norm(p[9] - p[0])))
    if scale < 1e-8:
        raise ValueError("degenerate palm scale")
    return PalmFrame(radial, longitudinal, normal, scale)


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ab = a - b
    cb = c - b
    denominator = float(np.linalg.norm(ab) * np.linalg.norm(cb))
    if denominator < 1e-8:
        return np.pi
    cosine = clamp(float(np.dot(ab, cb) / denominator), -1.0, 1.0)
    return float(np.arccos(cosine))


def _hinge_flexion(a: np.ndarray, b: np.ndarray, c: np.ndarray, full_scale: float = 2.15) -> float:
    return clamp((np.pi - _angle(a, b, c)) / full_scale)


def _finger_curl(p: np.ndarray, mcp: int, pip: int, dip: int, tip: int) -> float:
    """Estimate curl from the two observable hinges coupled by the O10."""
    proximal = _hinge_flexion(p[mcp], p[pip], p[dip])
    distal = _hinge_flexion(p[pip], p[dip], p[tip])
    return clamp(0.58 * proximal + 0.42 * distal)


def _feature_range(config: Mapping | None, name: str) -> tuple[float, float, bool]:
    item = ((config or {}).get("feature_ranges") or {}).get(name, {})
    low, high = DEFAULT_FEATURE_RANGES[name]
    return float(item.get("low", low)), float(item.get("high", high)), bool(item.get("invert", False))


def _calibrate(raw: float, name: str, config: Mapping | None) -> float:
    low, high, invert = _feature_range(config, name)
    value = normalize(raw, low, high)
    return 1.0 - value if invert else value


def _signed_proximal_spread(p: np.ndarray, frame: PalmFrame, mcp: int, pip: int, side: float) -> float:
    direction = _unit(p[pip] - p[mcp], f"finger {mcp}-{pip}")
    angle = float(np.arctan2(np.dot(direction, frame.radial), np.dot(direction, frame.longitudinal)))
    return side * angle


def extract_raw_features(points: Sequence[np.ndarray]) -> dict[str, float]:
    p = _points_array(points)
    frame = palm_frame(p)
    thumb_base = _unit(p[2] - p[1], "thumb metacarpal")
    thumb_plane = _unit(thumb_base - frame.normal * float(np.dot(thumb_base, frame.normal)), "thumb plane")
    thumb_roll_raw = float(np.arcsin(clamp(np.dot(thumb_base, frame.normal), -1.0, 1.0)))
    thumb_abad_raw = float(np.arctan2(np.dot(thumb_plane, frame.longitudinal), np.dot(thumb_plane, frame.radial)))
    thumb_base_curl = _hinge_flexion(p[1], p[2], p[3])
    thumb_tip_curl = _hinge_flexion(p[2], p[3], p[4])
    thumb_distance = float(np.linalg.norm(p[4] - p[0])) / frame.scale
    distance_curl = normalize(1.65 - thumb_distance, 0.0, 1.15)
    thumb_curl_raw = clamp(0.82 * max(thumb_base_curl, thumb_tip_curl) + 0.18 * distance_curl)
    # Use the middle MCP as a palm-centred reference.  Crossing toward the
    # little-finger side increases this value; camera position and hand size
    # cancel through the orthonormal frame and palm scale.
    thumb_cross_raw = -float(np.dot((p[4] - p[9]) / frame.scale, frame.radial))
    thumb_index_distance = float(np.linalg.norm(p[4] - p[8])) / frame.scale
    # A normalized distance below 0.45 is a deliberate tip-to-tip pinch on the
    # user's captures.  Saturating there lets a visually complete OK pose reach
    # the exact official target instead of stopping short due to detector noise.
    thumb_index_pinch = 1.0 - normalize(thumb_index_distance, 0.45, 0.85)
    thumb_chain = sum(float(np.linalg.norm(p[index + 1] - p[index]))
                      for index in (1, 2, 3))
    thumb_chord_ratio = (float(np.linalg.norm(p[4] - p[1])) /
                         max(thumb_chain, 1e-8))
    thumb_extension = normalize(thumb_chord_ratio, 0.90, 0.98)
    proximal_angles = []
    for mcp in (5, 9, 13, 17):
        direction = _unit(p[mcp + 1] - p[mcp], f"finger {mcp}-{mcp + 1}")
        proximal_angles.append(float(np.arctan2(np.dot(direction, frame.radial),
                                                np.dot(direction, frame.longitudinal))))
    # Parallel proximal phalanges distinguish the official PAPER pose from a
    # spread open hand without depending on global camera rotation.
    finger_parallel = 1.0 - normalize(float(np.std(proximal_angles)), 0.06, 0.20)
    return {
        "thumb_roll": thumb_roll_raw,
        "thumb_abad": thumb_abad_raw,
        "thumb_curl": thumb_curl_raw,
        "index_curl": _finger_curl(p, 5, 6, 7, 8),
        "middle_curl": _finger_curl(p, 9, 10, 11, 12),
        "ring_curl": _finger_curl(p, 13, 14, 15, 16),
        "pinky_curl": _finger_curl(p, 17, 18, 19, 20),
        "index_spread": _signed_proximal_spread(p, frame, 5, 6, +1.0),
        "ring_spread": _signed_proximal_spread(p, frame, 13, 14, -1.0),
        "pinky_spread": _signed_proximal_spread(p, frame, 17, 18, -1.0),
        "thumb_spread": thumb_abad_raw,
        "thumb_cross": thumb_cross_raw,
        "thumb_index_pinch": thumb_index_pinch,
        "thumb_extension": thumb_extension,
        "finger_parallel": finger_parallel,
    }


def extract_features(points: Sequence[np.ndarray], config: Mapping | None = None) -> RetargetFeatures:
    raw = extract_raw_features(points)
    return RetargetFeatures(**{field.name: _calibrate(raw[field.name], field.name, config)
                              for field in fields(RetargetFeatures)})


def _joint_norm(value: float, config: Mapping | None, joint_name: str) -> float:
    item = ((config or {}).get("joint_mapping") or {}).get(joint_name, {})
    value = 1.0 - value if bool(item.get("invert", False)) else value
    return clamp(float(item.get("offset", 0.0)) + float(item.get("gain", 1.0)) * value)


def _smoothstep(value: float, low: float, high: float) -> float:
    value = normalize(value, low, high)
    return value * value * (3.0 - 2.0 * value)


def fist_cross_activation(features: RetargetFeatures) -> float:
    """Return confidence that the thumb crosses a closed four-finger fist.

    Gating by both conditions is important: thumb opposition with open fingers
    must not create a fist, and the calibration fist intentionally keeps the
    thumb outside so it must not close the thumb automatically.
    """
    return clamp(_finger_closure_activation(features) *
                 _thumb_cross_activation(features))


def _finger_closure_activation(features: RetargetFeatures) -> float:
    finger_closure = np.mean((features.index_curl, features.middle_curl,
                              features.ring_curl, features.pinky_curl))
    return _smoothstep(float(finger_closure), 0.55, 0.88)


def _thumb_cross_activation(features: RetargetFeatures) -> float:
    return _smoothstep(features.thumb_cross, 0.72, 0.95)


def _spread_while_extended(spread: float, curl: float) -> float:
    """Reject abduction noise caused by projected/occluded curled fingers."""
    curled_gate = _smoothstep(curl, 0.30, 0.65)
    return clamp(spread * (1.0 - curled_gate))


def gesture_activations(features: RetargetFeatures) -> tuple[float, float]:
    """Return continuous PAPER and OK activation weights."""
    all_extended = 1.0 - _smoothstep(float(np.mean((features.index_curl,
                                                     features.middle_curl,
                                                     features.ring_curl,
                                                     features.pinky_curl))),
                                     0.10, 0.32)
    non_index_extended = 1.0 - _smoothstep(float(np.mean((features.middle_curl,
                                                          features.ring_curl,
                                                          features.pinky_curl))),
                                           0.10, 0.32)
    paper = clamp(all_extended * features.finger_parallel *
                  features.thumb_extension * (1.0 - features.thumb_index_pinch))
    ok = clamp(non_index_extended * features.thumb_extension *
               features.thumb_index_pinch)
    return paper, ok


def number_gesture_activations(features: RetargetFeatures) -> dict[str, float]:
    """Score the six number poses shipped by the O10 SDK.

    The four-finger pattern identifies each number.  Thumb extension separates
    the two otherwise identical pairs: NUM1/NUM8 and PAPER/NUM4.  Continuous
    scores prevent abrupt jumps near a classification boundary.
    """
    curls = {
        "index": features.index_curl,
        "middle": features.middle_curl,
        "ring": features.ring_curl,
        "pinky": features.pinky_curl,
    }
    extended = {name: 1.0 - _smoothstep(value, 0.18, 0.42)
                for name, value in curls.items()}
    # The user's calibrated NUM2 capture can report the curled little finger
    # near 0.46.  Keep the closed band wide enough for that pose while still
    # requiring a clear bend before a number preset can take over.
    curled = {name: _smoothstep(value, 0.30, 0.46)
              for name, value in curls.items()}
    thumb_extended = _smoothstep(features.thumb_extension, 0.35, 0.70)
    thumb_retracted = 1.0 - thumb_extended
    return {
        "num1": clamp(extended["index"] * curled["middle"] *
                      curled["ring"] * curled["pinky"] * thumb_retracted),
        "num2": clamp(extended["index"] * extended["middle"] *
                      curled["ring"] * curled["pinky"]),
        "num3": clamp(extended["index"] * extended["middle"] *
                      extended["ring"] * curled["pinky"]),
        "num4": clamp(extended["index"] * extended["middle"] *
                      extended["ring"] * extended["pinky"] * thumb_retracted),
        "num6": clamp(curled["index"] * curled["middle"] *
                      curled["ring"] * extended["pinky"] * thumb_extended),
        "num8": clamp(extended["index"] * curled["middle"] *
                      curled["ring"] * curled["pinky"] * thumb_extended),
    }


def all_gesture_activations(features: RetargetFeatures) -> dict[str, float]:
    """Return every official-pose score used by the retargeter."""
    paper, ok = gesture_activations(features)
    return {"paper": paper, "ok": ok, **number_gesture_activations(features)}


def _official_target(config: Mapping | None, model: O10RightModel,
                     name: str) -> list[float] | None:
    presets = (config or {}).get("gesture_presets") or {}
    target = presets.get(name)
    if target is None:
        return None
    order = tuple((config or {}).get("gesture_preset_joint_order") or ())
    if order and order != model.active_names:
        raise ValueError(f"official preset joint order mismatch: {order}")
    if len(target) != len(model.active):
        raise ValueError(f"official preset {name} expected 10 angles, got {len(target)}")
    return model.clamp_active([float(value) for value in target])


def retarget(features: RetargetFeatures, model: O10RightModel, config: Mapping | None = None) -> list[float]:
    closed_gate = _finger_closure_activation(features)
    crossed_gate = _thumb_cross_activation(features)
    # A 5x5 sweep of the actual O10 MJCF showed two stable fist targets: both
    # use about 75% roll; an outside thumb uses low opposition while a crossing
    # thumb uses about 75% opposition.  Base direction landmarks are
    # self-occluded in both cases, so closed fingers select this model-aware
    # target and thumb-tip position interpolates between the two.
    target_roll = 0.75
    target_abad = 0.25 + 0.50 * crossed_gate
    target_curl = max(features.thumb_curl, 0.30 + 0.38 * crossed_gate)
    thumb_roll = (1.0 - closed_gate) * features.thumb_roll + closed_gate * target_roll
    thumb_abad = (1.0 - closed_gate) * features.thumb_abad + closed_gate * target_abad
    thumb_curl = (1.0 - closed_gate) * features.thumb_curl + closed_gate * target_curl
    values = {
        "R_thumb_roll_joint": thumb_roll,
        "R_thumb_abad_joint": thumb_abad,
        "R_thumb_mcp_joint": thumb_curl,
        "R_index_abad_joint": _spread_while_extended(features.index_spread, features.index_curl),
        "R_index_pip_joint": features.index_curl,
        "R_middle_pip_joint": features.middle_curl,
        "R_ring_abad_joint": _spread_while_extended(features.ring_spread, features.ring_curl),
        "R_ring_pip_joint": features.ring_curl,
        "R_pinky_abad_joint": _spread_while_extended(features.pinky_spread, features.pinky_curl),
        "R_pinky_pip_joint": features.pinky_curl,
    }
    result = []
    for limit in model.active:
        norm = _joint_norm(values[limit.name], config, limit.name)
        result.append(limit.minimum + norm * (limit.maximum - limit.minimum))
    weighted_targets = []
    for name, weight in all_gesture_activations(features).items():
        preset = _official_target(config, model, name)
        if preset is not None and weight > 0.0:
            weighted_targets.append((weight, preset))
    total_weight = sum(weight for weight, _ in weighted_targets)
    scale = 1.0 / total_weight if total_weight > 1.0 else 1.0
    preset_weight = min(1.0, total_weight)
    base_weight = 1.0 - preset_weight
    result = [base_weight * value + sum(scale * weight * preset[index]
                                         for weight, preset in weighted_targets)
              for index, value in enumerate(result)]
    return result
