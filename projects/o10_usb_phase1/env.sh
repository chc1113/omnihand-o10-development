#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
  source "$ROOT_DIR/.venv/bin/activate"
fi
export O10_PHASE1_ROOT="$ROOT_DIR"
export O10_SDK_ROOT="$ROOT_DIR/sdk/agillink_omnihand_sdk-main"
if [[ -z "${O10_USB_PORT:-}" ]]; then
  O10_USB_PORT="$(find /dev/serial/by-id -maxdepth 1 -type l \
    -name 'usb-STMicroelectronics_STM32_Virtual_ComPort_*-if00' \
    -print -quit 2>/dev/null || true)"
  O10_USB_PORT="${O10_USB_PORT:-/dev/ttyACM0}"
fi
export O10_USB_PORT
export PYTHONPATH="$O10_SDK_ROOT/linux/x64/python${PYTHONPATH:+:$PYTHONPATH}"
echo "O10_PHASE1_ROOT=$O10_PHASE1_ROOT"
echo "O10_SDK_ROOT=$O10_SDK_ROOT"
echo "O10_USB_PORT=$O10_USB_PORT"
