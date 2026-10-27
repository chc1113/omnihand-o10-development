#!/usr/bin/env python3
"""Read-only O10 USB CDC observer.

This program initializes an O10 handle and only calls report/read APIs. It does
not set positions, angles, current limits, power, IDs, or control modes.
Results are written as JSON Lines so raw timing can be inspected later.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable


TACTILE_NAMES = ("thumb", "index", "middle", "ring", "little", "palm", "dorsum")
READ_METHODS = {
    "positions": "get_all_joint_positions",
    "angles": "get_all_active_joint_angles",
    "currents": "get_all_current_reports",
    "temperatures": "get_all_temperature_reports",
    "errors": "get_all_error_reports",
}


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def json_value(value: Any) -> Any:
    """Convert pybind values and error structs to JSON-safe summaries."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    try:
        return [json_value(item) for item in value]
    except TypeError:
        pass
    result: dict[str, Any] = {}
    for name in ("stalled", "overheat", "over_current", "motor_except", "commu_except"):
        for candidate in (name, f"{name}_", f"{name}__"):
            if hasattr(value, candidate):
                result[name] = bool(getattr(value, candidate))
                break
    return result or str(value)


def call_read(hand: Any, label: str, fn: Callable[[], Any]) -> tuple[dict[str, Any], Any]:
    start = time.monotonic_ns()
    try:
        value = fn()
        error = None
    except Exception as exc:  # Keep the observer alive to measure intermittent failures.
        value = None
        error = f"{type(exc).__name__}: {exc}"
    end = time.monotonic_ns()
    record = {
        "name": label,
        "started_monotonic_ns": start,
        "duration_ms": (end - start) / 1_000_000.0,
        "ok": error is None,
        "error": error,
        "value": json_value(value),
    }
    if isinstance(value, (list, tuple)):
        record["length"] = len(value)
    return record, value


def create_hand(port: str, hand_name: str, device_id: int) -> Any:
    from omnihand import HandType, OmniHand2025

    hand_type = HandType.LEFT if hand_name == "left" else HandType.RIGHT
    hand = OmniHand2025.create_hand_by_usb(
        hand_type=hand_type,
        hand_device_id=device_id,
        uart_port=port,
        baudrate=460800,
    )
    # Init is required to open the CDC connection. No command-writing API is
    # called by this observer after initialization.
    if not hand.init():
        raise RuntimeError(f"O10 USB 初始化失败: {port}")
    return hand


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 USB CDC 只读通讯/反馈频率监测")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--device-id", type=int, default=1)
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--poll-hz", type=float, default=5.0, help="完整读取周期目标频率")
    parser.add_argument("--mode", choices=("positions", "full"), default="full")
    parser.add_argument("--no-tactile", action="store_true", help="full 模式不读取 7 个降采样触觉区域")
    parser.add_argument("--show-wire", action="store_true", help="让 SDK 将每次 SND/RCV 十六进制帧打印到终端")
    parser.add_argument("--jsonl", type=Path, default=Path("usb_readonly.jsonl"))
    args = parser.parse_args()
    if args.seconds <= 0 or args.poll_hz <= 0:
        parser.error("seconds 和 poll-hz 必须大于 0")

    hand = create_hand(args.port, args.hand, args.device_id)
    if args.show_wire:
        hand.show_data_details(True)
    print(f"只读监测开始: port={args.port}, hand={args.hand}, seconds={args.seconds}, target_poll_hz={args.poll_hz}")
    print("安全边界: 仅读取位置/角度/电流/温度/错误/降采样触觉；不发送动作或参数写入命令。")

    args.jsonl.parent.mkdir(parents=True, exist_ok=True)
    cycle_records: list[dict[str, Any]] = []
    call_durations: dict[str, list[float]] = {}
    call_failures: dict[str, int] = {}
    tactile_counts: dict[str, list[int]] = {name: [] for name in TACTILE_NAMES}
    started = time.monotonic()
    next_deadline = started
    cycles = 0
    try:
        with args.jsonl.open("w", encoding="utf-8") as output:
            while time.monotonic() - started < args.seconds:
                cycle_start = time.monotonic_ns()
                calls: list[dict[str, Any]] = []
                if args.mode == "positions":
                    labels = ("positions",)
                else:
                    labels = tuple(READ_METHODS)
                for label in labels:
                    method_name = READ_METHODS[label]
                    call, _ = call_read(hand, label, getattr(hand, method_name))
                    calls.append(call)
                if args.mode == "full" and not args.no_tactile:
                    from omnihand import Finger

                    for enum_name, label in zip(
                        (Finger.THUMB, Finger.INDEX, Finger.MIDDLE, Finger.RING,
                         Finger.LITTLE, Finger.PALM, Finger.DORSUM), TACTILE_NAMES
                    ):
                        call, value = call_read(
                            hand, f"tactile_{label}",
                            lambda enum_name=enum_name: hand.get_tactile_sensor_data(enum_name),
                        )
                        calls.append(call)
                        if isinstance(value, (list, tuple)):
                            tactile_counts[label].append(len(value))
                cycle_end = time.monotonic_ns()
                cycle = {
                    "type": "cycle",
                    "wall_time": time.time(),
                    "cycle_index": cycles,
                    "cycle_duration_ms": (cycle_end - cycle_start) / 1_000_000.0,
                    "calls": calls,
                }
                output.write(json.dumps(cycle, ensure_ascii=False) + "\n")
                output.flush()
                cycle_records.append(cycle)
                cycles += 1
                for call in calls:
                    name = str(call["name"])
                    call_durations.setdefault(name, []).append(float(call["duration_ms"]))
                    if not call["ok"] or call.get("length") == 0:
                        call_failures[name] = call_failures.get(name, 0) + 1
                next_deadline += 1.0 / args.poll_hz
                sleep_for = next_deadline - time.monotonic()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_deadline = time.monotonic()
    except KeyboardInterrupt:
        print("收到 Ctrl-C，停止只读监测。")

    elapsed = max(time.monotonic() - started, 1e-9)
    cycle_durations = [float(item["cycle_duration_ms"]) for item in cycle_records]
    summary = {
        "type": "summary",
        "wall_time": time.time(),
        "elapsed_s": elapsed,
        "cycles": cycles,
        "actual_poll_hz": cycles / elapsed,
        "target_poll_hz": args.poll_hz,
        "cycle_duration_ms": {
            "mean": statistics.mean(cycle_durations) if cycle_durations else None,
            "p50": percentile(cycle_durations, 0.50),
            "p95": percentile(cycle_durations, 0.95),
            "p99": percentile(cycle_durations, 0.99),
            "max": max(cycle_durations) if cycle_durations else None,
        },
        "calls": {
            name: {
                "count": len(values),
                "mean_ms": statistics.mean(values),
                "p50_ms": percentile(values, 0.50),
                "p95_ms": percentile(values, 0.95),
                "p99_ms": percentile(values, 0.99),
                "max_ms": max(values),
                "fail_or_empty": call_failures.get(name, 0),
            }
            for name, values in call_durations.items()
        },
        "tactile_lengths": tactile_counts,
    }
    with args.jsonl.open("a", encoding="utf-8") as output:
        output.write(json.dumps(summary, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"原始记录: {args.jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
