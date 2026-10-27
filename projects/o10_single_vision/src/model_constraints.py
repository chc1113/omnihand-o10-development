"""O10 right-hand joint limits and passive-joint coupling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class JointLimit:
    name: str
    minimum: float
    maximum: float
    velocity: float


class O10RightModel:
    def __init__(self, spec: dict, source: Path):
        self.spec = spec
        self.source = source
        self.active = tuple(
            JointLimit(item["name"], item["min"], item["max"], item["velocity"])
            for item in spec["active_joints"]
        )
        if len(self.active) != 10:
            raise ValueError(f"O10 active joint count must be 10, got {len(self.active)}")
        self.active_names = tuple(item.name for item in self.active)

    @classmethod
    def from_json(cls, path: str | Path) -> "O10RightModel":
        path = Path(path)
        with path.open("r", encoding="utf-8") as stream:
            return cls(json.load(stream), path)

    @staticmethod
    def _polynomial(coefficients: list[float], value: float) -> float:
        result = 0.0
        for coefficient in reversed(coefficients):
            result = result * value + coefficient
        return result

    def clamp_active(self, angles: list[float] | tuple[float, ...]) -> list[float]:
        if len(angles) != len(self.active):
            raise ValueError(f"expected 10 active angles, got {len(angles)}")
        return [
            max(limit.minimum, min(limit.maximum, float(value)))
            for value, limit in zip(angles, self.active)
        ]

    def passive_from_active(self, angles: list[float] | tuple[float, ...]) -> dict[str, float]:
        active = self.clamp_active(angles)
        by_name = dict(zip(self.active_names, active))
        coupling = self.spec["coupling"]
        thumb_mcp = by_name["R_thumb_mcp_joint"]
        thumb_pip = coupling["thumb_pip"]
        thumb_dip = coupling["thumb_dip"]
        finger = coupling["finger_dip"]
        result = {
            "R_thumb_pip_joint": thumb_pip["multiplier"] * thumb_mcp + thumb_pip["offset"],
            "R_thumb_dip_joint": self._polynomial(thumb_dip["coefficients"], thumb_mcp),
        }
        for source, target in (
            ("R_index_pip_joint", "R_index_dip_joint"),
            ("R_middle_pip_joint", "R_middle_dip_joint"),
            ("R_ring_pip_joint", "R_ring_dip_joint"),
            ("R_pinky_pip_joint", "R_pinky_dip_joint"),
        ):
            result[target] = self._polynomial(finger["coefficients"], by_name[source])
        return result

    def all_joints(self, angles: list[float] | tuple[float, ...]) -> dict[str, float]:
        active = self.clamp_active(angles)
        result = dict(zip(self.active_names, active))
        result.update(self.passive_from_active(active))
        return result

