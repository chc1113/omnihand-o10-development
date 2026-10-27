"""Configuration loading with an optional generated calibration profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path, project: Path | None = None) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    profile = config.get("calibration_profile")
    if profile:
        profile_path = Path(profile)
        if not profile_path.is_absolute():
            profile_path = (project or path.parent) / profile_path
        if profile_path.is_file():
            with profile_path.open("r", encoding="utf-8") as stream:
                calibration = json.load(stream)
            config["feature_ranges"] = calibration.get("feature_ranges", {})
            config["calibration_loaded_from"] = str(profile_path)
            config["calibration_version"] = int(calibration.get("version", 0))
            config["calibration_anchor_pairs"] = calibration.get("anchor_pairs", {})
    preset_profile = config.get("gesture_preset_profile")
    if preset_profile:
        preset_path = Path(preset_profile)
        if not preset_path.is_absolute():
            preset_path = (project or path.parent) / preset_path
        if preset_path.is_file():
            with preset_path.open("r", encoding="utf-8") as stream:
                presets = json.load(stream)
            config["gesture_presets"] = presets.get("active_joint_angles", {})
            config["gesture_preset_joint_order"] = presets.get("active_joint_order", [])
            config["gesture_presets_loaded_from"] = str(preset_path)
    return config
