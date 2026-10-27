"""Narrow, lazily imported adapter for an O10 right hand over USB CDC."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any


class O10UsbHand:
    def __init__(self, port: str, device_id: int = 1):
        from omnihand import HandType, OmniHand2025

        self.port = str(Path(port).resolve()) if Path(port).exists() else port
        self._hand: Any = OmniHand2025.create_hand_by_usb(
            hand_type=HandType.RIGHT,
            hand_device_id=int(device_id),
            uart_port=self.port,
            baudrate=460800,
        )
        if self._hand is None or not self._hand.init():
            raise RuntimeError(f"O10 USB initialization failed: {self.port}")

    def vendor_summary(self) -> str:
        try:
            return str(self._hand.get_vendor_info())
        except Exception as exc:
            return f"vendor info unavailable: {type(exc).__name__}: {exc}"

    def read_angles(self) -> list[float]:
        values = [float(value) for value in self._hand.get_all_active_joint_angles()]
        if len(values) != 10 or not all(math.isfinite(value) for value in values):
            raise RuntimeError(f"invalid O10 angle feedback: {values}")
        return values

    def read_errors(self) -> list[str]:
        reports = self._hand.get_all_error_reports()
        active = []
        for index, report in enumerate(reports, start=1):
            flags = []
            for name in ("stalled", "overheat", "over_current", "motor_except", "commu_except"):
                for candidate in (name, f"{name}_", f"{name}__"):
                    if hasattr(report, candidate) and bool(getattr(report, candidate)):
                        flags.append(name)
                        break
            if flags:
                active.append(f"joint {index}: {','.join(flags)}")
        return active

    def write_angles(self, values: list[float]) -> None:
        if len(values) != 10 or not all(math.isfinite(float(value)) for value in values):
            raise ValueError("refusing malformed O10 target")
        self._hand.set_all_active_joint_angles([float(value) for value in values])
