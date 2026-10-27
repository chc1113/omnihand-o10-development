# AGILINK OmniHand SDK 新手上手指南

本文以 **OmniHand 2025（O10）** 为例，使用 **Linux x86_64 + USB 直连** 完成左手、右手以及左右手同时操作。

如果你只想先让一只手动起来，请按“快速操作”从上到下执行即可。左手和右手使用同一套官方 demo，主要区别是 `-t left/right` 和 USB 串口路径。

## 1. 先确认你使用的型号和连接方式

本指南适用于：

- 型号：**OmniHand 2025（O10，10 个主动自由度）**
- 手型：**左手或右手**
- 通信方式：**USB CDC 直连**
- 系统：Ubuntu/Linux x86_64

O10 通过 USB 传输控制数据，但 **USB 不负责给灵巧手供电**。使用 USB 控制前，请确认灵巧手已经连接并打开 24V 电源。

单手连接关系如下：

```text
[电脑] -- USB 数据线 --> [OmniHand O10 左手/右手]
                                  |
                              24V 电源
```

如果同时使用左右手，连接关系如下：

```text
[电脑] -- USB --> [OmniHand O10 左手]
       \
        \-- USB --> [OmniHand O10 右手]

每只手都需要独立的 24V 电源。
```

如果你的电脑是 ARM64/aarch64，请把下面命令中的 `linux/x64` 替换为 `linux/aarch64`。

## 2. 快速操作

### 2.1 进入仓库目录

```bash
cd /home/chc/agillink_omnihand_sdk-main
```

如果仓库路径不同，请替换成你自己的路径。

### 2.2 安装 SDK

```bash
cd linux/x64
./install.sh
```

安装脚本会自动完成：

- 安装 C++ SDK 和动态库
- 根据当前 Python 版本安装匹配的 `omnihand` wheel
- 保留 Python、C++ 和 ROS2 示例

请注意：运行 demo 时使用的 `python3` 必须和安装 SDK 时使用的是同一个 Python。
如果你看到命令行前面有 `(base)`，建议显式使用当前环境的 Python 安装：

```bash
python3 -m pip install --force-reinstall \
  python/omnihand-1.1.5-cp314-cp314-linux_x86_64.whl
```

上面命令中的 `cp314` 要和你的 Python 版本对应。先查看版本：

```bash
python3 --version
```

对应关系为：Python 3.10 使用 `cp310`，3.11 使用 `cp311`，3.12 使用
`cp312`，3.13 使用 `cp313`，3.14 使用 `cp314`。

安装后立即验证：

```bash
python3 -c "from omnihand import OmniHand2025; print('omnihand SDK OK')"
```

### 2.3 配置 USB 权限

首次使用 USB 设备时执行：

```bash
sudo ./setup_udev.sh
```

执行完成后，**注销并重新登录**，或者重启电脑。然后重新插拔 USB 线。

### 2.4 检查 USB 串口

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

常见结果是：

```text
/dev/ttyACM0
```

如果没有看到串口，请检查：

1. 灵巧手是否已上电。
2. USB 线是否同时支持数据传输。
3. USB 线是否插牢。
4. 重新插拔 USB 后再次执行上面的命令。

也可以查看更稳定的设备名称：

```bash
ls -l /dev/serial/by-id/
```

例如可以使用类似下面的路径代替 `/dev/ttyACM0`：

```text
/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_XXXX-if00
```

### 2.5 检查 Python SDK

```bash
python3 -c "from omnihand import OmniHand2025, HandType; print('omnihand SDK OK')"
```

看到 `omnihand SDK OK` 就表示 Python SDK 已安装成功。

## 3. 第一次运行：读取左手或右手硬件信息

先不要控制动作，使用官方 demo 读取设备信息。只连接左手时：

```bash
cd /home/chc/agillink_omnihand_sdk-main

python3 linux/x64/python/demo/omnihand_2025/demo_get_hardware_info.py \
  -d usb \
  -t left \
  --hand-id 1 \
  --uart-port /dev/ttyACM0
```

只连接右手时，把 `-t left` 改成 `-t right`：

```bash
python3 linux/x64/python/demo/omnihand_2025/demo_get_hardware_info.py \
  -d usb \
  -t right \
  --hand-id 1 \
  --uart-port /dev/ttyACM0
```

参数含义：

| 参数 | 含义 |
|---|---|
| `-d usb` | 使用 USB CDC 通信 |
| `-t left` | 使用左手 |
| `-t right` | 使用右手 |
| `--hand-id 1` | 灵巧手设备 ID，出厂通常为 1 |
| `--uart-port /dev/ttyACM0` | 当前这只手的 USB 串口路径 |

成功时，输出中应能看到类似内容：

```text
[USB][serial port: /dev/ttyACM0] init [ok]
Product Model: O10
Active Degrees of Freedom: 10
Hand Device ID: 1
```

左手和右手的 `hand-id` 通常都可以是 `1`，因为它们通过不同 USB 串口分别连接。  
如果某只手的设备 ID 不是 1，请把对应命令中的 `--hand-id 1` 改成实际 ID。

## 4. 控制左手或右手做动作

官方动作 demo 是一个交互式菜单。控制左手：

```bash
python3 linux/x64/python/demo/omnihand_2025/demo_set_motion.py \
  -d usb \
  -t left \
  --hand-id 1 \
  --uart-port /dev/ttyACM0
```

控制右手时，只需要把 `-t left` 改成 `-t right`：

```bash
python3 linux/x64/python/demo/omnihand_2025/demo_set_motion.py \
  -d usb \
  -t right \
  --hand-id 1 \
  --uart-port /dev/ttyACM0
```

运行后会看到动作菜单。输入数字并按回车：

| 输入 | 动作 |
|---:|---|
| `0` | 回到零位，第一次运行建议先执行 |
| `1` | 张开手掌 |
| `2` | 握拳 1 |
| `3` | 握拳 2 |
| `4` | OK 手势 |
| `5` | 单手比心 |
| `6` | 点赞 |
| `7` | ILY 手势 |
| `8` - `13` | 数字手势 |
| `14` - `16` | 双手比心动作中的单手姿态 |
| `17` | 合十 |
| `99` | 退出 demo |

建议第一次按以下顺序操作：

```text
0    回到零位
1    张开手掌
2    握拳
0    回到零位
99   退出
```

运行动作 demo 前，请确认：

- 手指周围没有被夹住的物体。
- 灵巧手放在稳定位置。
- 不要直接把手指放在关节活动范围内。
- 第一次只执行一个动作，确认动作幅度正常后再继续。

## 5. 左右手同时连接和操作

### 5.1 识别两只手的 USB 串口

同时插入左手和右手后执行：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
ls -l /dev/serial/by-id/
```

可能看到：

```text
/dev/ttyACM0
/dev/ttyACM1
```

不要只根据 `ttyACM0` 或 `ttyACM1` 判断左右手，因为重新插拔后编号可能变化。推荐使用 `/dev/serial/by-id/` 下的稳定路径，并先分别运行硬件信息 demo 确认哪一个串口对应哪只手。

### 5.2 分别测试左右手

假设确认结果如下：

```bash
LEFT_PORT=/dev/ttyACM0
RIGHT_PORT=/dev/ttyACM1
```

在两个终端中都执行上面的变量设置。每个终端只需要使用对应的串口。

先分别读取信息：

```bash
python3 linux/x64/python/demo/omnihand_2025/demo_get_hardware_info.py \
  -d usb -t left --hand-id 1 --uart-port "$LEFT_PORT"

python3 linux/x64/python/demo/omnihand_2025/demo_get_hardware_info.py \
  -d usb -t right --hand-id 1 --uart-port "$RIGHT_PORT"
```

### 5.3 同时控制左右手

当前仓库中的 USB 官方 `demo_set_motion.py` 一次控制一只手，不支持直接传入 `both`。要同时控制左右手，请打开两个终端。

终端 1 控制左手：

```bash
cd /home/chc/agillink_omnihand_sdk-main
python3 linux/x64/python/demo/omnihand_2025/demo_set_motion.py \
  -d usb -t left --hand-id 1 --uart-port "$LEFT_PORT"
```

终端 2 控制右手：

```bash
cd /home/chc/agillink_omnihand_sdk-main
python3 linux/x64/python/demo/omnihand_2025/demo_set_motion.py \
  -d usb -t right --hand-id 1 --uart-port "$RIGHT_PORT"
```

然后分别在两个终端输入动作编号。例如：

```text
左手终端：1   张开左手
右手终端：2   让右手握拳
左手终端：0   左手回零
右手终端：0   右手回零
两个终端：99  分别退出
```

### 5.4 同时读取左右手触觉

同样打开两个终端，分别执行官方触觉 demo：

```bash
python3 linux/x64/python/demo/omnihand_2025/demo_tactile_sensor.py \
  -d usb -t left --hand-id 1 --uart-port "$LEFT_PORT"
```

```bash
python3 linux/x64/python/demo/omnihand_2025/demo_tactile_sensor.py \
  -d usb -t right --hand-id 1 --uart-port "$RIGHT_PORT"
```

## 6. 单手读取触觉传感器

O10 的官方触觉 demo 会读取拇指、食指、中指、无名指、小拇指、手心和手背的数据：

```bash
python3 linux/x64/python/demo/omnihand_2025/demo_tactile_sensor.py \
  -d usb \
  -t left \
  --hand-id 1 \
  --uart-port /dev/ttyACM0
```

输出示例：

```text
Thumb tactile data: 0 g
Index tactile data: 0 g
Middle tactile data: 0 g
Ring tactile data: 0 g
Little tactile data: 0 g
Palm tactile data: 0 g
Dorsum tactile data: 0 g
```

没有接触物体时读到 0 或较小数值是正常现象。

## 7. 常用命令模板

左右手使用同一套命令，只需要修改 `HAND` 和 `PORT`：

```bash
HAND=left
PORT=/dev/ttyACM0

python3 linux/x64/python/demo/omnihand_2025/demo_get_hardware_info.py \
  -d usb -t "$HAND" --hand-id 1 --uart-port "$PORT"

python3 linux/x64/python/demo/omnihand_2025/demo_set_motion.py \
  -d usb -t "$HAND" --hand-id 1 --uart-port "$PORT"

python3 linux/x64/python/demo/omnihand_2025/demo_tactile_sensor.py \
  -d usb -t "$HAND" --hand-id 1 --uart-port "$PORT"
```

右手示例：

```bash
HAND=right
PORT=/dev/ttyACM0
python3 linux/x64/python/demo/omnihand_2025/demo_set_motion.py \
  -d usb -t "$HAND" --hand-id 1 --uart-port "$PORT"
```

查看所有官方 demo：

```bash
find linux/x64/python/demo/omnihand_2025 -maxdepth 1 -type f -name 'demo_*.py' -printf '%f\n' | sort
```

查看某个 demo 支持的参数：

```bash
python3 linux/x64/python/demo/omnihand_2025/demo_set_motion.py --help
```

## 8. 常见问题

### 7.1 `No module named 'omnihand'`

说明 Python wheel 没有安装到当前使用的 Python 环境。确认 `python3` 与安装时使用的是同一个 Python：

```bash
which python3
python3 --version
python3 -m pip show omnihand
```

然后重新安装：

```bash
cd linux/x64
./install.sh
```

如果系统禁止直接写入系统 Python，可以手动安装匹配版本的 wheel。例如 Python 3.14：

```bash
python3 -m pip install python/omnihand-1.1.5-cp314-cp314-linux_x86_64.whl
```

### 7.2 找不到 `/dev/ttyACM0`

先重新插拔 USB，再执行：

```bash
lsusb
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

如果串口编号变成 `/dev/ttyACM1`，就把命令中的 `/dev/ttyACM0` 改为 `/dev/ttyACM1`。

### 7.3 `Permission denied`

重新执行 USB 权限配置：

```bash
cd linux/x64
sudo ./setup_udev.sh
```

然后注销并重新登录。也可以确认当前用户属于 `dialout` 组：

```bash
groups
```

### 7.4 初始化成功但手不动

按下面顺序检查：

1. 确认灵巧手已连接 24V 电源。
2. 确认使用的是 `-d usb`，不是默认的 `-d zlgcan`。
3. 确认手型参数正确：左手使用 `-t left`，右手使用 `-t right`。
4. 确认 `--uart-port` 指向当前存在的串口。
5. 先在动作 demo 中输入 `0`，再尝试其他动作。
6. 确认手指没有被外物卡住。

### 7.5 不知道自己的 Python 版本对应哪个 wheel

```bash
python3 --version
ls linux/x64/python/*.whl
```

例如：

- Python 3.10 对应 `cp310`
- Python 3.11 对应 `cp311`
- Python 3.12 对应 `cp312`
- Python 3.13 对应 `cp313`
- Python 3.14 对应 `cp314`

## 9. 仓库目录说明

```text
linux/x64/
├── install.sh                         SDK 安装脚本
├── setup_udev.sh                      USB 权限配置脚本
├── python/
│   ├── *.whl                          Python SDK 安装包
│   └── demo/omnihand_2025/            O10 官方 Python demo
├── cpp/                               C++ SDK、头文件和示例
└── ros2/                              ROS2 运行包

doc/zh_cn/
├── QUICK_START.md                     官方快速入门
├── TROUBLESHOOTING.md                 官方故障排除
├── API_PYTHON_O10.md                  O10 Python API
└── API_ROS2_O10.md                    O10 ROS2 接口
```

## 10. 进一步开发

- [O10 Python API](doc/zh_cn/API_PYTHON_O10.md)
- [O10 C++ API](doc/zh_cn/API_CPP_O10.md)
- [O10 ROS2 接口](doc/zh_cn/API_ROS2_O10.md)
- [官方快速入门](doc/zh_cn/QUICK_START.md)
- [官方故障排除](doc/zh_cn/TROUBLESHOOTING.md)

## 许可证

Mulan PSL v2 - Copyright (c) 2025, Agibot Co., Ltd.
