# O10 Ubuntu 22.04 二次开发项目

本目录把两个方向拆成相互独立的项目：

- `vision_tracking`：本机摄像头、MediaPipe 手部关键点、10 关节重定向。
- `tactile_interaction`：O10 触觉读取、基线校准、接触事件记录。

两者都使用 AGILINK OmniHand SDK 的 O10 Python 接口，但不互相依赖。默认情况下程序只显示/记录数据，不驱动真机；只有显式传入 `--live` 才会发送关节命令。

## 硬件判断

该方案可行，前提是：

1. Ubuntu 22.04、Python 3.10 及以上。
2. O10 从 CANFD 口获得稳定 24 V 供电；USB 线只负责数据通信，不能替代供电。
3. O10 USB CDC 设备枚举为 `/dev/ttyACM0`（也可能是 `/dev/ttyUSB0`）。
4. 摄像头能被 OpenCV 打开，通常为 `/dev/video0`。

## SDK 安装

在 SDK 发布包目录执行：

```bash
cd agillink_omnihand_sdk-main/agillink_omnihand_sdk-main/linux/x64
./install.sh
sudo ./setup_udev.sh
# 注销并重新登录，使 dialout/plugdev 权限生效
python3 -c "from omnihand import OmniHand2025; print('omnihand import ok')"
```

检查设备：

```bash
ls -la /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
ls -la /dev/video*
```

O10 USB 建议使用 `baudrate=460800`、请求间隔 100--500 ms、帧超时 200--500 ms。首次上电先用官方硬件信息和触觉示例验证，不要直接运行闭合动作。

## 安装项目依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r o10_projects/vision_tracking/requirements.txt
```

触觉项目只需要 SDK 和标准库；视觉项目额外需要 OpenCV、MediaPipe 和 NumPy。
USB CDC 使用逐区域 `get_tactile_sensor_data()` 读取降采样触觉；全分辨率
`get_all_tactile_sensor_data_raw()` 依赖 CAN 后端，在 USB 私有协议下可能为空。

## 运行顺序

先做官方 USB 例程：

```bash
cd agillink_omnihand_sdk-main/agillink_omnihand_sdk-main/linux/x64/python
python3 test/test_omnihand_2025_usb.py -p /dev/ttyACM0 -f 100 -t 500
python3 demo/omnihand_2025/demo_get_hardware_info.py -d usb --uart-port /dev/ttyACM0
python3 demo/omnihand_2025/demo_tactile_sensor.py -d usb --uart-port /dev/ttyACM0
```

再运行本目录的 dry-run：

```bash
python3 o10_projects/tactile_interaction/tactile_monitor.py --port /dev/ttyACM0 --seconds 10
python3 o10_projects/vision_tracking/visual_teleop.py --camera 0
```

确认画面、关节映射和触觉数据正常后，才运行视觉真机模式：

```bash
python3 o10_projects/vision_tracking/visual_teleop.py \
  --camera 0 --hand right --port /dev/ttyACM0 --live
```

按 `q` 或 `Esc` 退出。首次 `--live` 应让手处于空旷位置，并准备好断电或急停手段。

## 当前边界

SDK 官方没有 O10 摄像头视觉追踪例程；公众号中的“单摄像头视觉驱动”需要自行完成关键点到 O10 关节的重定向。本目录提供的是可运行的入门实现，不是经过抓取任务标定的工业控制器。视觉映射应先做小幅度、低频率和空载测试，再逐步提高频率。
