#!/usr/bin/env bash
set -euo pipefail

# This script only adjusts the current shell. It does not install packages or
# write to the existing AGILINK SDK directory.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/.venv/bin/activate" ]]; then
  # Activate only this bundle's private environment when available.
  source "$SCRIPT_DIR/.venv/bin/activate"
fi

if [[ "${1-}" != "" ]]; then
  export AGILINK_SDK_ROOT="$1"
fi

if [[ -n "${AGILINK_SDK_ROOT-}" && -d "$AGILINK_SDK_ROOT/linux/x64/python" ]]; then
  # A wheel installed by setup_env.sh is preferred. PYTHONPATH is retained for
  # deployments that expose an unpacked omnihand package.
  export PYTHONPATH="$AGILINK_SDK_ROOT/linux/x64/python${PYTHONPATH:+:$PYTHONPATH}"
  echo "AGILINK_SDK_ROOT=$AGILINK_SDK_ROOT"
  echo "PYTHONPATH 已加入现有 SDK Python 目录（未修改 SDK）"
else
  echo "未设置 AGILINK_SDK_ROOT；将使用系统已安装的 omnihand Python 包。"
fi
