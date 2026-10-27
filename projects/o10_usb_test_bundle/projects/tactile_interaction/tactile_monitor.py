"""O10 USB tactile monitor and contact-event logger.

This is intentionally read-only: it never commands a motor. It first samples
an unloaded baseline and then reports regions whose mean tactile value rises
above baseline by a configurable threshold.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path


def create_hand(hand_name: str, port: str):
    from omnihand import HandType, OmniHand2025

    hand_type = HandType.LEFT if hand_name == "left" else HandType.RIGHT
    hand = OmniHand2025.create_hand_by_usb(
        hand_type=hand_type,
        hand_device_id=OmniHand2025.kDefaultHandDeviceId,
        uart_port=port,
        baudrate=460800,
    )
    hand.set_request_interval(100)
    hand.set_frame_recv_timeout(500)
    if not hand.init():
        raise RuntimeError(f"O10 USB 初始化失败: {port}")
    return hand


def read_means(hand) -> dict[str, float]:
    # USB CDC uses the private StreamCmd protocol. Full-resolution Raw batch
    # reads are implemented by public CAN backends and can be empty on USB.
    from omnihand import Finger

    sensors = (
        (Finger.THUMB, "thumb"),
        (Finger.INDEX, "index"),
        (Finger.MIDDLE, "middle"),
        (Finger.RING, "ring"),
        (Finger.LITTLE, "little"),
        (Finger.PALM, "palm"),
        (Finger.DORSUM, "dorsum"),
    )
    values: dict[str, float] = {}
    for sensor_id, name in sensors:
        data = list(hand.get_tactile_sensor_data(sensor_id))
        if data:
            values[name] = sum(data) / len(data)
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 触觉读取和接触事件记录")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--baseline-seconds", type=float, default=2.0)
    parser.add_argument("--threshold", type=float, default=8.0, help="相对基线的平均值阈值，单位约为 g")
    parser.add_argument("--csv", type=Path, default=None)
    args = parser.parse_args()

    hand = create_hand(args.hand, args.port)
    print(f"请保持手部空载，正在校准 {args.baseline_seconds:.1f} 秒...")
    baseline_samples: list[dict[str, float]] = []
    end = time.monotonic() + args.baseline_seconds
    while time.monotonic() < end:
        baseline_samples.append(read_means(hand))
        time.sleep(0.1)
    names = sorted({name for sample in baseline_samples for name in sample})
    baseline = {
        name: sum(sample.get(name, 0.0) for sample in baseline_samples) / max(len(baseline_samples), 1)
        for name in names
    }
    print("基线:", ", ".join(f"{name}={value:.1f}" for name, value in baseline.items()))

    output = args.csv.open("w", newline="", encoding="utf-8") if args.csv else None
    writer = csv.writer(output) if output else None
    if writer:
        writer.writerow(["timestamp", *names, "contacts"])

    try:
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            sample = read_means(hand)
            contacts = [name for name in names if sample.get(name, 0.0) - baseline[name] >= args.threshold]
            timestamp = time.time()
            print(time.strftime("%H:%M:%S", time.localtime(timestamp)),
                  "contacts=" + ("|".join(contacts) if contacts else "none"),
                  " ".join(f"{name}:{sample.get(name, 0.0):.1f}" for name in names))
            if writer:
                writer.writerow([timestamp, *(f"{sample.get(name, 0.0):.3f}" for name in names), "|".join(contacts)])
                output.flush()
            time.sleep(0.1)
    finally:
        if output:
            output.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
