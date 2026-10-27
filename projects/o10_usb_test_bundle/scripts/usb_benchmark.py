#!/usr/bin/env python3
"""O10 USB CDC frequency benchmark.

Default mode is dry-run (connection/import checks only). With --live, send a
small 10-joint sinusoidal position command at the selected frequency and report
loop timing. This is a benchmark, not a production controller.
"""

from __future__ import annotations

import argparse
import math
import statistics
import time


SAFE_POS = [2048, 2048, 4096, 2048, 4096, 4096, 2048, 4096, 2048, 4096]


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(math.ceil(q * len(ordered))) - 1))
    return ordered[index]


def create_hand(port: str, hand_name: str):
    from omnihand import HandType, OmniHand2025

    hand_type = HandType.LEFT if hand_name == "left" else HandType.RIGHT
    hand = OmniHand2025.create_hand_by_usb(
        hand_type=hand_type,
        hand_device_id=OmniHand2025.kDefaultHandDeviceId,
        uart_port=port,
        baudrate=460800,
    )
    # These setters may be no-ops for serial backends; application timing below
    # is authoritative for this benchmark.
    hand.set_request_interval(0)
    hand.set_frame_recv_timeout(500)
    if not hand.init():
        raise RuntimeError(f"O10 USB 初始化失败: {port}")
    return hand


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 USB CDC 位置控制频率基准")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--frequency", type=float, default=5.0)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--amplitude", type=int, default=20, help="tick 振幅，建议 20")
    parser.add_argument("--live", action="store_true", help="实际发送小幅动作；默认不动作")
    args = parser.parse_args()

    if args.frequency <= 0 or args.frequency > 50:
        raise SystemExit("frequency 必须在 0～50 Hz；建议从 5 Hz 开始")
    if args.seconds <= 0:
        raise SystemExit("seconds 必须大于 0")
    if args.amplitude < 1 or args.amplitude > 100:
        raise SystemExit("amplitude 建议在 1～100 tick")

    print(f"目标频率: {args.frequency:.2f} Hz，时长: {args.seconds:.1f} s")
    print(f"模式: {'LIVE（将驱动 O10）' if args.live else 'DRY-RUN（不会驱动 O10）'}")
    if not args.live:
        print("未传入 --live；仅检查参数，不打开设备、不发送命令。")
        return 0

    hand = create_hand(args.port, args.hand)
    period = 1.0 / args.frequency
    durations: list[float] = []
    overruns = 0
    failures = 0
    count = 0
    start = time.monotonic()
    next_deadline = start
    try:
        while time.monotonic() - start < args.seconds:
            loop_start = time.monotonic()
            phase = 2.0 * math.pi * 0.25 * (loop_start - start)
            target = list(SAFE_POS)
            delta = int(round(args.amplitude * math.sin(phase)))
            # Move only a few flexion ticks around the neutral target.
            for index in (2, 4, 5, 7, 9):
                target[index] = max(0, min(4095, SAFE_POS[index] + delta))
            try:
                hand.set_all_joint_positions(target)
            except Exception as exc:  # continue to collect failure rate
                failures += 1
                if failures <= 3:
                    print("调用失败:", repr(exc))
            elapsed = time.monotonic() - loop_start
            durations.append(elapsed * 1000.0)
            count += 1
            if elapsed > period:
                overruns += 1
            next_deadline += period
            sleep_for = next_deadline - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)
    except KeyboardInterrupt:
        print("收到 Ctrl-C，停止测试。")
    finally:
        # Return to the same small neutral target; no full close/open motion.
        try:
            hand.set_all_joint_positions(SAFE_POS)
        except Exception:
            pass

    elapsed_total = max(time.monotonic() - start, 1e-9)
    print("\n=== 结果 ===")
    print(f"样本数: {count}")
    print(f"实际循环频率: {count / elapsed_total:.2f} Hz")
    if durations:
        print(f"调用耗时 ms: mean={statistics.mean(durations):.3f}, "
              f"P95={percentile(durations, 0.95):.3f}, "
              f"P99={percentile(durations, 0.99):.3f}, "
              f"max={max(durations):.3f}")
    print(f"周期超期: {overruns} ({(overruns / max(count, 1)) * 100:.3f}%)")
    print(f"调用失败: {failures} ({(failures / max(count, 1)) * 100:.3f}%)")
    print("判断建议：P99 耗时应小于周期，超期率尽量低于 0.1%，且无停顿/断连。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
