#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "视觉环境不存在，请先运行: bash $PROJECT_DIR/scripts/setup_env.sh"
  exit 2
fi
cd "$PROJECT_DIR"
exec "$PYTHON" scripts/real_hand_camera.py "$@"
