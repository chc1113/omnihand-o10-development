# O10 USB 第一阶段：只读通讯观测

此目录是独立项目目录。官方压缩包已从 `/home/chc/agillink_omnihand_sdk-main.zip` 重新解压到：

```text
/home/chc/O10/o10_usb_phase1/sdk/agillink_omnihand_sdk-main
```

这里不引用、也不修改 `/home/chc/agillink_omnihand_sdk-main` 那份已改动 SDK。

## 当前设备

当前已枚举：

```text
/dev/ttyACM0
/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_386833633335-if00
```

优先使用 `by-id` 稳定路径。当前 SDK 版本为 1.1.5，Linux x86_64，提供 Python 3.10～3.14 wheel。

## 安装独立环境

```bash
cd /home/chc/O10/o10_usb_phase1
chmod +x setup_env.sh env.sh scripts/usb_readonly_monitor.py scripts/usb_wire_probe.py
./setup_env.sh
source ./env.sh
python -c 'import omnihand; print(omnihand.__file__)'
```

安装脚本只在本目录创建 `.venv`，从本目录的 SDK wheel 安装；不会执行或修改原 SDK 的 `install.sh`。

## 第一阶段只读监测

先确认 O10 已从 CANFD 口获得稳定 24 V，手指周围空旷，且没有 Toolbox/其他程序占用串口。监测程序会初始化 USB 连接，但不会发送位置、角度、电流阈值、功率、ID 或控制模式写入命令。

```bash
python scripts/usb_readonly_monitor.py \
  --port "$O10_USB_PORT" \
  --hand right \
  --seconds 30 \
  --poll-hz 5 \
  --mode full \
  --jsonl records/full_5hz.jsonl
```

只测位置反馈调用耗时和轮询频率：

```bash
python scripts/usb_readonly_monitor.py \
  --port "$O10_USB_PORT" --seconds 60 --poll-hz 10 \
  --mode positions --jsonl records/positions_10hz.jsonl
```

如果需要先降低请求量，可以在 `full` 模式中跳过 7 个触觉区域：

```bash
python scripts/usb_readonly_monitor.py \
  --port "$O10_USB_PORT" --seconds 30 --poll-hz 5 \
  --mode full --no-tactile --jsonl records/full_no_tactile.jsonl
```

需要查看 SDK 打印的每次线级 SND/RCV 帧时，加上 `--show-wire`。只建议短时间运行，因为完整模式每周期会产生多组帧：

```bash
python scripts/usb_readonly_monitor.py \
  --port "$O10_USB_PORT" --seconds 2 --poll-hz 2 \
  --mode positions --show-wire --jsonl records/wire_positions.jsonl
```

## 记录内容

每一行 `type=cycle` 包含：

- 周期开始墙上时间和单周期总耗时；
- 每个 SDK 读取调用的开始时间、耗时、是否成功、返回长度和返回值；
- 位置、角度、电流、温度、错误状态；
- 7 个降采样触觉区域及其点数。

末行 `type=summary` 汇总实际轮询频率和各调用的 mean/P50/P95/P99/max 延迟、空返回/异常次数。这里的“反馈频率”是应用主动轮询得到的有效反馈频率，不代表设备内部传感器原始采样频率；O10 触觉硬件文档标称约 10 Hz。

## USB 协议静态要点

SDK 将 O10 Type-C 作为 USB CDC 串口，默认 `460800` baud，使用私有 `StreamCmd` 协议。官方 C++ USB 测试源码位于：

```text
sdk/agillink_omnihand_sdk-main/linux/x64/cpp/test/test_omnihand_2025_usb.cc
```

源码列出的主要命令包括：

| 功能 | StreamCmd |
|---|---:|
| 单/批量位置读写 | `0x06`/`0x07`, `0x08`/`0x09` |
| 电流、速度、温度读取 | `0x0A`、`0x0B`、`0x0C` |
| 错误读取 | `0x0D` |
| 降采样触觉 | `0x11` |
| 位置/速度/电流混合控制 | `0x32` |
| 固件/厂商信息 | `0xCD` |

当前监测器不直接抓取串口字节流，而是通过官方 Python binding 记录调用级请求/响应耗时，避免第二个进程抢占串口。若后续需要字节级帧解析，应在停用 SDK 访问后使用串口抓包或在 SDK C++ 层增加日志，不能与在线控制程序并行监听同一串口。

运行线级只读探针（只查询厂商信息和设备信息）：

```bash
python scripts/usb_wire_probe.py --port "$O10_USB_PORT" --hand right
```

已观测到的帧格式为：

```text
EE AA | device_id(2B, little-endian) | length(1B) | command+payload | crc(2B)
```

`length` 是 `command` 字节加 payload 的长度；整帧长度为 `7 + length` 字节。一次实测的厂商信息请求为：

```text
SND: EE AA 01 00 01 CD 35 2A
RCV: EE AA 01 00 0B CD 02 54 31 01 02 07 03 00 00 0A 6E 12
```

其中 `CD` 是厂商/固件信息命令，响应 payload 含产品类型、版本和 DOF；`C2` 命令用于读取产品序列号。CRC 字节由 SDK 生成和校验，本阶段只记录，不自行重算。

位置和触觉帧的实测例子：

```text
# 批量位置反馈：09 + 20 字节 little-endian 位置
SND: EE AA 01 00 01 09 FD B3
RCV: EE AA 01 00 15 09 9D 0F 1A 08 46 00 5D 08 66 04 2D 02 66 08 5D 02 BE 07 90 01 73 D9

# 单区域降采样触觉：11 + sensor_index；返回长度由区域决定
SND: EE AA FF 07 02 11 00 E1 18
RCV: EE AA 01 00 12 11 00 [16 个触觉字节] [CRC 2B]
```

本次设备返回的 `09` 位置向量为 `[3997, 2074, 70, 2141, 1126, 557, 2137, 605, 1973, 400]`。触觉请求使用 `device_id=0x07ff` 的广播/区域寻址形式；手指区域实际返回 16 点，手心和手背各返回 25 点。

## 判断标准

- `positions` 模式实际轮询频率接近目标，且无空返回/异常；
- P99 单次读取耗时应显著小于轮询周期；
- `full` 模式下触觉读取不应造成持续超期或串口断连；
- 位置反馈频率和触觉有效更新频率分开统计；
- 当前阶段只做读，不执行 `--live`、位置写入或官方带动作的全套测试。
