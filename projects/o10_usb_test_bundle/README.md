# O10 USB 直连测试独立交接包

这个目录是一个与现有 `agillink_omnihand_sdk-main` 隔离的测试包。它不修改、不覆盖 SDK，也不要求把 SDK 复制进本包。

## 使用原则

1. Ubuntu 22.04 上解压本包到新的目录。
2. 只读引用已经部署并调通的 AGILINK SDK。
3. 先执行预检和官方 USB 只读例程，再做小幅动作。
4. 视觉程序默认 dry-run；只有明确传入 `--live` 才会驱动 O10。
5. 基准测试默认不动作；只有传入 `--live` 才进行小幅往返运动。

## 目录

```text
o10_usb_test_bundle/
├── README.md
├── USB直连O10测试_工作交接文档.md
├── env.sh                         # 只设置环境变量，不改 SDK
├── scripts/
│   ├── preflight_readonly.sh      # Ubuntu/设备/权限/摄像头只读检查
│   ├── run_official_usb_checks.sh # 调用已部署 SDK 的官方 USB 检查
│   └── usb_benchmark.py           # 5/10/20/30/50 Hz 频率基准测试
└── projects/
    ├── vision_tracking/           # 摄像头视觉项目，默认 dry-run
    └── tactile_interaction/       # USB 降采样触觉读取项目
```

## 第一次运行

```bash
cd <本包解压目录>/o10_usb_test_bundle
chmod +x setup_env.sh env.sh scripts/*.sh
./setup_env.sh /path/to/already/deployed/agillink_omnihand_sdk-main
source ./env.sh /path/to/already/deployed/agillink_omnihand_sdk-main
./scripts/preflight_readonly.sh
```

`setup_env.sh` 会在本包内部创建 `.venv`，从已经部署的 SDK 目录读取匹配当前 Python 的 wheel，并安装到本包自己的虚拟环境。它不执行 SDK 的 `install.sh`、不执行 `setup_udev.sh`，也不写入或覆盖 SDK 目录。以后只需 `source ./env.sh` 即可进入本包环境。

如果 SDK 已经通过 wheel 安装到系统 Python，也可以跳过 `setup_env.sh`，直接：

```bash
source ./env.sh
```

## 官方 USB 检查

```bash
./scripts/run_official_usb_checks.sh /dev/ttyACM0 right
```

脚本默认只运行硬件信息和降采样触觉读取。官方 USB 全套 pytest 会改变/读取更多状态，需人工确认后单独执行：

```bash
cd /path/to/already/deployed/agillink_omnihand_sdk-main/linux/x64/python
python3 test/test_omnihand_2025_usb.py -p /dev/ttyACM0 -f 500 -t 200
```

## 项目运行

触觉只读监视：

```bash
python3 projects/tactile_interaction/tactile_monitor.py \
  --port /dev/ttyACM0 --hand right --seconds 20 --csv tactile.csv
```

视觉 dry-run：

```bash
python3 projects/vision_tracking/visual_teleop.py --camera 0
```

视觉真机模式必须由人工确认后执行，并先从 5～10 秒小幅动作开始：

```bash
python3 projects/vision_tracking/visual_teleop.py \
  --camera 0 --hand right --port /dev/ttyACM0 --live
```

## USB 频率基准测试

先查看帮助：

```bash
python3 scripts/usb_benchmark.py --help
```

默认只做协议/参数检查，不驱动电机。实测时建议从 5 Hz 开始：

```bash
python3 scripts/usb_benchmark.py \
  --port /dev/ttyACM0 --hand right --frequency 5 --seconds 60 --live
```

依次测试 5、10、20、30、50 Hz。只使用很小的往返幅度；出现异常立即按 Ctrl-C 并断电。

## 重要硬件要求

- O10 必须由 CANFD 口获得稳定 24 V 供电；Type-C 只负责数据。
- 手周围保持空旷，不能让手指夹住物体或靠近人体。
- 不能同时打开 Toolbox、官方例程和本包程序访问同一个串口。
- `/dev/ttyACM0` 只是常见名称，以预检脚本实际显示为准。

详细流程、证据、故障排查和记录模板见 `USB直连O10测试_工作交接文档.md`。
