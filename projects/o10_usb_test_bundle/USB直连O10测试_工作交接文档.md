# O10 灵巧手 USB 直连测试工作交接文档

> 交接目的：将当前 Windows 工作区中的分析、代码和测试结论带到 Ubuntu 22.04，使用 O10 Type-C USB CDC 直连完成设备识别、只读检查、小幅动作测试、触觉读取和 USB 通信频率基准测试。
>
> 本文面向第一次接触 O10 SDK 的同学。进入 Ubuntu 后，请先让 Codex 读取本文件，再按“安全检查 → 官方例程 → 小幅动作 → 频率测试”的顺序执行。

## 1. 项目背景与当前结论

- 灵巧手型号：Agibot OmniHand 2025 O10（10 个主动关节）。
- 操作系统：Ubuntu 22.04。
- 当前可用通信：O10 Type-C USB 直连；暂时没有 ZLG/HCAN USB-CANFD 适配器。
- 摄像头：Ubuntu 主机自带摄像头，通常为 `/dev/video0`。
- SDK：`agillink_omnihand_sdk`，当前工作区保存有 SDK 压缩包和解压目录。
- 当前判断：USB CDC 可以连续发送批量位置命令，不是“完全不能做连贯动作”；但官方没有给 USB CDC 提供 CANFD 那样的 100 Hz 长时可靠性示例。高频、低抖动、视觉与触觉并行闭环仍应优先 CANFD。

### USB 与 CANFD 的关键区别

这里必须区分两种“USB”：

1. **O10 Type-C USB CDC 直连**：电脑 USB → O10，SDK 使用 `create_hand_by_usb()`，默认 460800 baud，走串行私有 StreamCmd 协议。
2. **ZLG USB-CANFD**：电脑 USB → ZLG 适配器 → O10 CANFD，SDK 使用 `create_hand_by_zlgcan()`；电脑侧虽然插 USB，但手侧通信是 CANFD。

官方仓库证据：

- `linux/x64/python/test/test_omnihand_2025_usb.py`：USB 测试默认 460800 baud、请求间隔 500 ms、接收超时 200 ms，并覆盖位置、状态、降采样触觉和批量 PT/PVT 混合控制。
- `linux/x64/python/demo/omnihand_2025/demo_100set_and_20tactile_reliability.py`：明确测试 100 Hz 位置控制 + 10 Hz 触觉，控制周期 10 ms；该示例没有 USB CDC 选项，主要面向 CANFD/RS485/TCP。
- `doc/zh_cn/API_ROS2_O10.md`：全分辨率 Raw 触觉一次多帧读取要求公共 CAN 后端；USB 私有协议下 Raw 可能为空。
- `doc/zh_cn/API_PYTHON_O10.md`：O10 触觉传感器真实采样频率为 10 Hz；关节速度限制约 0.164 或 0.308 rad/s。
- `linux/x64/cpp/include/omnihand/omnihand.h`：USB/RS485 不支持电流阈值接口；部分单关节位置接口在 USB 无回包时可能返回 `-1`；发送超时设置仅对 ZLG CANFD 有效。

## 2. 硬件与安全要求

### 必须确认

- O10 必须从 **CANFD 口获得稳定 24 V 供电**。Type-C USB 线只负责数据通信，不能代替电源。
- 测试时手掌、手指周围保持空旷，不要夹持物体，不要把手指放在关节运动范围内。
- 第一次动作只允许小幅度（约行程的 5%～10%），先用低频率测试。
- 保持可以立即断电的手段；发现异常噪声、持续抖动、温升、失控或通信异常时立即断电。
- USB 测试过程中不要同时打开官方 Toolbox、其他串口程序或第二个 SDK 进程。

### 典型连接

```text
24 V 电源 ──> O10 CANFD 供电接口
Ubuntu 电脑 ──Type-C USB──> O10 USB 数据接口
Ubuntu 摄像头 ──> /dev/video0（仅视觉项目需要）
```

## 3. 进入 Ubuntu 后，先让 Codex 执行的检查

把本文件复制到 Ubuntu 项目目录后，对 Codex 说：

```text
请先完整读取 USB直连O10测试_工作交接文档.md。不要直接驱动灵巧手。
先检查当前工作目录、SDK 解压位置、Python 版本、USB 串口设备和摄像头设备，
然后根据文档给出下一步检查结果；任何会让手运动的命令都先征得我确认。
```

Codex 首轮只应做以下只读检查：

```bash
pwd
find . -maxdepth 3 -type d -name 'agillink_omnihand_sdk*' -o -name 'o10_projects'
python3 --version
ls -la /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
ls -la /dev/video* 2>/dev/null || true
groups
```

如果看到了 `/dev/ttyACM0`，先记录实际设备名。若只有权限错误，优先检查当前用户是否属于 `dialout`，不要用 root 长期运行程序。

## 4. SDK 安装与导入检查

以下路径中的 `<SDK_ROOT>` 需要替换成 Ubuntu 实际路径。通常 SDK 目录下应有 `linux/x64`、`install.sh` 和 `python` 文件夹。

```bash
cd <SDK_ROOT>/linux/x64
./install.sh
sudo ./setup_udev.sh
```

注销并重新登录后检查：

```bash
python3 -c "from omnihand import OmniHand2025, Finger, HandType; print('omnihand import ok')"
```

若使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
```

视觉项目额外安装：

```bash
python3 -m pip install -r <PROJECT_ROOT>/o10_projects/vision_tracking/requirements.txt
```

## 5. 官方 USB 例程执行顺序

进入 SDK 的 Python 目录：

```bash
cd <SDK_ROOT>/linux/x64/python
```

### 第一步：官方 USB 只读/基础测试

先运行默认保守参数：

```bash
python3 test/test_omnihand_2025_usb.py \
  -p /dev/ttyACM0 \
  -f 500 \
  -t 200
```

通过标准：

- 能成功打开设备；
- 能读取设备信息、10 轴位置/电流/速度/温度/错误状态；
- 能读取每个手指的 16 点降采样触觉以及手心/手背的 25 点降采样触觉；
- 没有持续超时、串口断开或异常退出。

### 第二步：硬件信息和触觉例程

```bash
python3 demo/omnihand_2025/demo_get_hardware_info.py \
  -d usb --uart-port /dev/ttyACM0

python3 demo/omnihand_2025/demo_tactile_sensor.py \
  -d usb --uart-port /dev/ttyACM0
```

注意：USB 下优先使用 `get_tactile_sensor_data()` 逐区域读取降采样数据。不要把 ROS2 的全分辨率 Raw 触觉接口作为 USB 是否正常的判断标准；Raw 批量读取主要依赖 CAN 后端。

## 6. 小幅动作测试（需要人工确认后执行）

动作测试前确认：手周围空旷、24 V 电源稳定、急停/断电手段可用。

先运行 SDK 自带运动例程的帮助信息，确认参数：

```bash
python3 demo/omnihand_2025/demo_set_motion.py -h
```

然后只做低幅度、低频率、短时间动作。推荐先使用本工作区的视觉程序 dry-run，不发送真机命令：

```bash
python3 <PROJECT_ROOT>/o10_projects/vision_tracking/visual_teleop.py --camera 0
```

确认摄像头画面、关键点和关节映射都正常后，再由 Codex 解释将要发送的命令，人工确认后才允许 `--live`。第一次 live 测试只保持 5～10 秒，并将手放在空旷位置：

```bash
python3 <PROJECT_ROOT>/o10_projects/vision_tracking/visual_teleop.py \
  --camera 0 \
  --hand right \
  --port /dev/ttyACM0 \
  --live
```

程序支持按 `q` 或 `Esc` 退出。若动作突然变大、停顿、抖动或通信报错，立即退出并断电。

## 7. USB 通信频率基准测试

### 目标

不要直接接受“USB 只有 2 Hz”或“USB 一定能 100 Hz”这样的结论。需要在这只 O10、这台 Ubuntu 电脑和这根 USB 线上测量：

1. 仅发送 10 轴批量位置；
2. 发送位置并读取位置反馈；
3. 发送位置，同时以 5～10 Hz 读取降采样触觉。

### 建议频率阶梯

```text
5 Hz → 10 Hz → 20 Hz → 30 Hz → 50 Hz
```

每档先跑 60 秒；稳定档再跑 10 分钟。第一次只做小幅正弦或往返目标，不做全行程握拳。

### 每档记录

- 目标频率和实际循环频率；
- 单次 SDK 调用耗时：平均值、P95、P99、最大值；
- 周期超时次数；
- 空返回、异常、串口断开次数；
- 位置反馈是否持续滞后；
- 视频中是否出现明显阶梯、停顿或抖动；
- 同时读取触觉后，控制周期是否明显变长。

### 建议通过标准

```text
P99 单次调用耗时 < 控制周期
周期超期率 < 0.1%
无断连、无连续超时
无明显停顿或失控
位置滞后不持续增大
```

如果需要编写基准程序，优先复用 SDK 的 `set_all_joint_positions()`，并在应用层用 `time.monotonic()` 定时；不要把 `set_request_interval()` 当作 USB 的实时保证，因为 SDK 文档说明该设置主要针对 CAN，USB/串行实现可能不生效或意义不同。

## 8. 视觉与触觉项目边界

两个方向可以、也建议作为两个独立项目维护：

### 视觉追踪项目

- 输入：本机摄像头、MediaPipe 手部关键点；
- 输出：10 个 O10 主动关节目标；
- 初期只做 dry-run 和小幅低频 live；
- 必须加入滤波、死区、角度限幅和每周期最大变化量；
- 摄像头 30 FPS 不等于 O10 控制 30/100 Hz，视觉推理和通信要分别测量。

### 触觉交互项目

- USB 下使用逐区域降采样接口；
- O10 触觉硬件真实采样频率约 10 Hz；
- 可实现接触检测、阈值判断、停止/放松动作等简单闭环；
- 全分辨率 Raw 阵列读取和更高可靠性的触觉闭环建议迁移到 CANFD。

视觉与触觉联合时，建议先采用：

```text
位置控制：10～20 Hz
触觉查询：5～10 Hz
同一线程内避免每次位置命令后立即查询所有传感器
```

## 9. 常见故障排查

### 找不到 `/dev/ttyACM0`

```bash
dmesg --follow
lsusb
ls -la /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

重新插拔 USB，确认线缆支持数据传输而不是仅充电。不要在多个程序间同时占用串口。

### Permission denied

```bash
groups
sudo usermod -aG dialout "$USER"
```

注销并重新登录后再次检查。优先修复用户组权限，不建议每次用 `sudo python3`。

### 能打开串口但读取超时

- 确认 O10 CANFD 口已供 24 V；
- 确认选择了正确的左右手类型和设备 ID；
- 确认没有 Toolbox 或其他程序占用；
- 将请求间隔恢复到 500 ms、帧超时 200～500 ms；
- 记录完整报错，不要反复快速重启多个测试进程。

### 动作不连贯

按以下顺序定位：

1. 先看视觉推理帧率；
2. 再看应用层命令发送周期；
3. 再看 SDK 调用 P99 耗时和超时；
4. 再看位置反馈滞后；
5. 最后考虑 O10 关节本身的 0.164/0.308 rad/s 速度限制。

## 10. 什么时候购买 CANFD 适配器

当前只有 USB 时可以继续开发，不必停工。出现以下任一需求时，建议购买单通道 ZLG USB-CANFD-100U 类设备：

- 需要稳定的 20～30 Hz 以上视觉遥操作；
- 需要 100 Hz 位置控制可靠性验证；
- 需要位置、状态和触觉并行闭环；
- 需要全分辨率 Raw 触觉；
- USB 基准测试出现周期超时、抖动或断连；
- 需要长期无人值守运行。

单手单通道即可；只有未来同时控制左右两只手时，才考虑双通道 200U。

## 11. 当前工作区已有文件

Windows 工作区中已经准备：

- `o10_projects/README.md`：整体项目说明和运行顺序；
- `o10_projects/vision_tracking/visual_teleop.py`：视觉追踪入门程序，默认 dry-run，`--live` 才驱动真机；
- `o10_projects/vision_tracking/requirements.txt`：视觉依赖；
- `o10_projects/tactile_interaction/tactile_monitor.py`：USB 触觉读取与接触事件记录，使用逐区域降采样接口；
- `agillink_omnihand_sdk-main/`：官方 SDK 解压目录（Ubuntu 需重新确认实际路径）。

程序迁移到 Ubuntu 后，先做 Python 语法检查和 import 检查，再连接实物。不要把 Windows 路径（如 `D:\...`）直接复制到 Ubuntu 命令中。

## 12. 每次测试后的记录模板

```text
日期：
Ubuntu 版本：
Python 版本：
SDK 版本/commit：
O10 左手/右手：
USB 设备名：
USB 线/供电情况：

测试类型：只读 / 小幅动作 / 视觉 dry-run / 视觉 live / 触觉 / 频率基准
目标频率：
实际频率：
平均耗时：
P95/P99 耗时：
超时次数：
异常/断连次数：
动作现象：
触觉数据现象：
结论：通过 / 降低频率 / 修改程序 / 需要 CANFD
完整日志文件：
```

## 13. 交接完成判定

当以下项目都完成后，才算 USB 直连测试阶段完成：

- [ ] Ubuntu 能导入 `omnihand`；
- [ ] 找到正确的 `/dev/ttyACM*` 设备；
- [ ] 官方 USB 基础测试通过；
- [ ] 官方硬件信息和降采样触觉测试通过；
- [ ] 小幅动作测试安全完成；
- [ ] 视觉项目 dry-run 正常；
- [ ] 至少完成 5/10/20 Hz USB 频率基准；
- [ ] 记录超时、断连和位置滞后数据；
- [ ] 根据实测结果决定继续 USB 或采购 CANFD。

