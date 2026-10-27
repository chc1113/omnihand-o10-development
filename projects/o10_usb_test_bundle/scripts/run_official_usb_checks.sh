#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-/dev/ttyACM0}"
HAND="${2:-right}"

if [[ -z "${AGILINK_SDK_ROOT-}" ]]; then
  echo "请先 source ../env.sh /path/to/already/deployed/agillink_omnihand_sdk-main"
  exit 2
fi

PY_DIR="$AGILINK_SDK_ROOT/linux/x64/python"
if [[ ! -d "$PY_DIR" ]]; then
  echo "SDK Python 目录不存在：$PY_DIR"
  exit 2
fi

echo "将只读调用现有 SDK：$PY_DIR"
echo "串口：$PORT；手型：$HAND"
echo "本脚本不运行 install.sh，不修改 SDK。"

pushd "$PY_DIR" >/dev/null
python3 demo/omnihand_2025/demo_get_hardware_info.py -d usb --uart-port "$PORT"
python3 demo/omnihand_2025/demo_tactile_sensor.py -d usb --uart-port "$PORT"
popd >/dev/null
