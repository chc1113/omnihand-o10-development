"""Fail-closed shaping for O10 simulation and real-hardware targets."""

from __future__ import annotations

import math
import time

from model_constraints import O10RightModel


class SafeTargetLimiter:
    def __init__(self, model: O10RightModel, max_step_fraction: float = 0.015,
                 workspace_fraction: float = 0.10,
                 velocity_scale: float = 1.0):
        if not 0 < max_step_fraction <= 1 or not 0 < workspace_fraction <= 1:
            raise ValueError("safety fractions must be in (0,1]")
        if not math.isfinite(velocity_scale) or velocity_scale <= 0:
            raise ValueError("velocity_scale must be positive and finite")
        self.model = model
        self.max_step_fraction = max_step_fraction
        self.workspace_fraction = workspace_fraction
        self.velocity_scale = float(velocity_scale)
        self.previous: list[float] | None = None
        self.initial: list[float] | None = None
        self.last_time: float | None = None

    def reset(self, current: list[float], now: float | None = None) -> None:
        if len(current) != 10 or not all(math.isfinite(float(x)) for x in current):
            raise ValueError("measured position must contain ten finite angles")
        self.previous = self.model.clamp_active(current)
        self.initial = list(self.previous)
        self.last_time = time.monotonic() if now is None else float(now)

    def update(self, target: list[float], now: float | None = None) -> list[float]:
        if self.previous is None or self.initial is None or self.last_time is None:
            raise RuntimeError("limiter must be reset from a measured position before use")
        if len(target) != 10 or not all(math.isfinite(float(x)) for x in target):
            raise ValueError("target must contain ten finite angles")
        now = time.monotonic() if now is None else float(now)
        dt = max(0.0, min(now - self.last_time, 0.20))
        target = self.model.clamp_active(target)
        result: list[float] = []
        for old, initial, desired, limit in zip(self.previous, self.initial, target, self.model.active):
            span = limit.maximum - limit.minimum
            envelope_low = max(limit.minimum, initial - span * self.workspace_fraction)
            envelope_high = min(limit.maximum, initial + span * self.workspace_fraction)
            desired = max(envelope_low, min(envelope_high, desired))
            step = min(span * self.max_step_fraction,
                       limit.velocity * self.velocity_scale * dt)
            result.append(max(old - step, min(old + step, desired)))
        self.previous = result
        self.last_time = now
        return result
