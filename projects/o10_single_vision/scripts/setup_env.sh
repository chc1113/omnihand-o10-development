#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3.10}"
VENV="$PROJECT_DIR/.venv"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "未找到 Python: $PYTHON_BIN"
  exit 2
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv --without-pip "$VENV"
fi

SITE_PACKAGES="$($VENV/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
"$PYTHON_BIN" -m pip install --upgrade --target "$SITE_PACKAGES" -r "$PROJECT_DIR/requirements.txt"

SDK_WHEEL="$PROJECT_DIR/../o10_usb_phase1/sdk/agillink_omnihand_sdk-main/linux/x64/python/omnihand-1.1.5-cp310-cp310-linux_x86_64.whl"
if [[ -f "$SDK_WHEEL" ]]; then
  "$PYTHON_BIN" -m pip install --upgrade --target "$SITE_PACKAGES" "$SDK_WHEEL"
fi

"$VENV/bin/python" -c 'import cv2, mediapipe, numpy, omnihand; print("视觉及 O10 SDK 环境就绪:", cv2.__version__, mediapipe.__version__, numpy.__version__)'
