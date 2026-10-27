#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SDK_ROOT="${ROOT_DIR}/sdk/agillink_omnihand_sdk-main"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -d "$SDK_ROOT/linux/x64/python" ]]; then
  echo "独立 SDK 不存在：$SDK_ROOT" >&2
  exit 2
fi

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"
fi
source "$ROOT_DIR/.venv/bin/activate"
python -m pip install --upgrade pip

python_tag="cp$(python -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')"
wheel="$(find "$SDK_ROOT/linux/x64/python" -maxdepth 1 -type f -name "omnihand-*.whl" -name "*-${python_tag}-${python_tag}-*.whl" | sort | head -n 1)"
if [[ -z "$wheel" ]]; then
  echo "没有找到匹配当前 Python 的 omnihand wheel（当前 Python: $(python --version)）" >&2
  find "$SDK_ROOT/linux/x64/python" -maxdepth 1 -type f -name 'omnihand-*.whl' -printf '可用: %f\n'
  exit 2
fi

python -m pip install --force-reinstall "$wheel"
cat > "$ROOT_DIR/.phase1_env" <<EOF
SDK_ROOT=$SDK_ROOT
OMNIHAND_WHEEL=$wheel
EOF
echo "独立环境已准备：$ROOT_DIR/.venv"
echo "SDK wheel：$wheel"
echo "后续执行：source $ROOT_DIR/env.sh"
