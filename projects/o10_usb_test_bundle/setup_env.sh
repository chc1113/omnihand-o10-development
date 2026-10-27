#!/usr/bin/env bash
set -euo pipefail

# Install the already-deployed SDK wheel into this bundle's private venv.
# The source SDK directory is read-only from this script's perspective.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SDK_ROOT="${1:-${AGILINK_SDK_ROOT-}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -z "$SDK_ROOT" ]]; then
  echo "用法: $0 /path/to/already/deployed/agillink_omnihand_sdk-main"
  exit 2
fi

WHEEL_DIR="$SDK_ROOT/linux/x64/python"
if [[ ! -d "$WHEEL_DIR" ]]; then
  echo "未找到 SDK wheel 目录: $WHEEL_DIR"
  exit 2
fi

if [[ ! -d "$SCRIPT_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$SCRIPT_DIR/.venv"
fi
source "$SCRIPT_DIR/.venv/bin/activate"
python -m pip install --upgrade pip

python_tag="cp$(python -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')"
wheel="$(find "$WHEEL_DIR" -maxdepth 1 -type f -name "omnihand-*-${python_tag}-${python_tag}-*.whl" | head -n 1)"
if [[ -z "$wheel" ]]; then
  echo "没有找到与当前 Python 匹配的 omnihand wheel。当前 Python: $(python --version)"
  find "$WHEEL_DIR" -maxdepth 1 -type f -name 'omnihand-*.whl' -printf '可用: %f\n'
  exit 2
fi

python -m pip install --force-reinstall "$wheel"
python -m pip install -r "$SCRIPT_DIR/projects/vision_tracking/requirements.txt"
cat > "$SCRIPT_DIR/.venv_config" <<EOF
AGILINK_SDK_ROOT=$SDK_ROOT
OMNIHAND_WHEEL=$wheel
EOF
echo "独立环境已创建: $SCRIPT_DIR/.venv"
echo "SDK wheel 已复制安装到本包虚拟环境，原 SDK 未修改。"
echo "后续运行前执行: source $SCRIPT_DIR/env.sh"
