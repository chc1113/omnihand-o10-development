#!/usr/bin/env python3
"""Read-only USB CDC wire probe for two identification requests.

The SDK prints SND/RCV hex frames when show_data_details(True) is enabled. This
probe deliberately asks only for vendor and device information, so it does not
write positions, power, IDs, limits, or control modes.
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="O10 USB CDC 线级只读探针")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--hand", choices=("left", "right"), default="right")
    parser.add_argument("--device-id", type=int, default=1)
    args = parser.parse_args()

    from omnihand import HandType, OmniHand2025

    hand_type = HandType.LEFT if args.hand == "left" else HandType.RIGHT
    hand = OmniHand2025.create_hand_by_usb(
        hand_type=hand_type,
        hand_device_id=args.device_id,
        uart_port=args.port,
        baudrate=460800,
    )
    if not hand.init():
        raise RuntimeError(f"O10 USB 初始化失败: {args.port}")
    hand.show_data_details(True)
    print("仅请求厂商信息和设备信息；以下 SND/RCV 为 SDK 输出的 USB CDC 十六进制帧。")
    print("VendorInfo:", hand.get_vendor_info())
    print("DeviceInfo:", hand.get_device_info())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
