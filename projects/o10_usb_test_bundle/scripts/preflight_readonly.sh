#!/usr/bin/env bash
set -u

echo "=== O10 USB 独立测试包：只读预检 ==="
echo "时间: $(date -Is)"
echo "目录: $(pwd)"
echo
echo "[系统]"
uname -a
python3 --version 2>&1 || true
echo
echo "[用户组]"
id
echo
echo "[USB 串口设备]"
shopt -s nullglob
ports=(/dev/ttyACM* /dev/ttyUSB*)
if ((${#ports[@]})); then
  ls -l "${ports[@]}"
else
  echo "未发现 /dev/ttyACM* 或 /dev/ttyUSB*"
fi
echo
echo "[摄像头设备]"
cams=(/dev/video*)
if ((${#cams[@]})); then
  ls -l "${cams[@]}"
else
  echo "未发现 /dev/video*"
fi
echo
echo "[Python SDK 导入]"
python3 - <<'PY'
try:
    import omnihand
    from omnihand import OmniHand2025, Finger, HandType
    print("omnihand import ok")
    print("OmniHand2025:", OmniHand2025)
except Exception as exc:
    print("omnihand import failed:", repr(exc))
PY
echo
echo "预检完成：本脚本没有打开串口，也没有驱动灵巧手。"
