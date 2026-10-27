# O10 单视觉项目

本项目独立管理摄像头采集、MediaPipe 手部关键点、手势识别、模型约束下的连续重定向和受保护的 O10 真机桥接。仿真入口不导入 O10 SDK；只有 `run_real.sh` 在双重解锁后才允许发送命令。

## 目录结构

```text
o10_single_vision/
├── .venv/                  # 项目独立 Python 3.10 环境
├── config/vision.json      # 摄像头与识别参数
├── config/omnihand_right_model.json # O10右手10轴与耦合约束
├── src/hand_action_recognition.py    # 离散动作识别
├── src/retargeting.py                 # 正交掌坐标、关键点到10主动关节
├── src/vision_pipeline.py             # 右手筛选、世界关键点选择
├── src/model_constraints.py           # 限位与被动关节
├── src/safe_controller.py             # 仅做限幅/限速，不开串口
├── scripts/setup_env.sh               # 重建/更新环境
├── scripts/run.sh                     # 启动动作识别
├── scripts/preview_retargeting.py     # 连续角度预览，不控制真机
├── scripts/calibrate_all.py           # 一键引导标定并生成个人参数
├── scripts/solve_calibration.py       # 从样本求解个人特征范围
├── scripts/validate_model.py          # 校验模型顺序
├── scripts/sim_hand_camera.py         # 摄像头驱动 MuJoCo 虚拟手
├── scripts/real_hand_camera.py        # 受保护的摄像头真机控制
├── logs/                   # 动作变化 JSONL 记录
├── data/                   # 后续样本与标定数据
└── docs/                   # 后续设计与测试文档
```

## 启动

```bash
cd projects/o10_single_vision  # 从仓库根目录开始
bash scripts/run.sh
```

把一只手放到摄像头前，可识别：

- `OPEN`：张开手掌
- `FIST`：握拳
- `POINT`：食指指向
- `PINCH`：拇指与食指捏合
- `HAND`：检测到手，但不属于以上姿态
- `NO_HAND`：没有检测到手

窗口中会显示 21 个关键点、左右手判断、弯曲量、捏合距离和实时帧率。按 `q` 或 `Esc` 退出。

## 连续重定向预览

```bash
bash scripts/run.sh  # 离散动作识别
.venv/bin/python scripts/validate_model.py
.venv/bin/python scripts/preview_retargeting.py --camera 0
```

预览窗口显示10个主动关节角和6个由模型耦合关系计算出的被动关节角，始终不会访问 O10 串口。

版本 5 使用真正的正交掌坐标系。四指外展取 MCP 到 PIP 的近节指骨方向，四指屈曲使用已由现场效果验证的 PIP/DIP 角度；手指弯曲时会逐渐关闭容易受遮挡干扰的侧移信号。拇指方向、局部弯曲和“指尖横跨掌心”分别计算；完整握拳依据 O10 模型关节扫描结果。对于张开并拢且同平面的 PAPER 手势，以及拇指食指捏合的 OK 手势，程序使用连续置信度将视觉映射收敛到官方 SDK 1.1.5 的右手预置角度，手势之间仍保持平滑过渡。程序优先使用 MediaPipe 世界关键点，并只接收置信度达标的右手。

## MuJoCo 虚拟手仿真

先运行 `bash scripts/setup_env.sh` 安装含 MuJoCo 3.10.0 的项目环境。下列命令均在本子项目目录中执行。启动摄像头驱动的虚拟右手：

```bash
.venv/bin/python scripts/validate_model.py
bash scripts/run_sim.sh
```

会同时打开 MuJoCo 虚拟手窗口和摄像头输入窗口。你的手部动作只改变虚拟模型；程序不导入 O10 SDK、不打开 `/dev/ttyACM0`、不发送实体关节命令。按摄像头窗口的 `q`/`Esc` 或关闭 MuJoCo 窗口退出。

若只想检查模型是否能加载，可运行：

```bash
bash scripts/run_sim.sh --no-camera
```

## 标定采集

推荐运行一键标定。按窗口提示摆好姿态，每项按空格并保持 2 秒。版本 3 新增“完整握拳”（拇指横放在拳面），用来区别原有的“四指握拳”（拇指留在拳外）：

```bash
.venv/bin/python scripts/calibrate_all.py
```

如果七项旧标定已经完成，只补采完整握拳即可；程序会保留其他姿态：

```bash
.venv/bin/python scripts/calibrate_all.py --poses full_fist
```

原始 21 点、原始特征和置信度保存在 `data/calibration_samples.jsonl`，求解结果写入 `config/calibration_right.json`，仿真和真机入口都会自动加载。真机入口在缺少该文件时拒绝动作。

## 真机步骤

先连接 O10 的独立 24 V 电源和 USB CDC 数据线，确保手的运动范围内没有人手、线缆和物体。先做只读探测：

```bash
bash scripts/run_real.sh --probe-only
```

只有只读探测无错误、个人标定完成、仿真方向经人眼确认后，才运行：

```bash
bash scripts/run_real.sh --arm REAL_HAND
```

真机窗口连续识别右手 12 帧后显示 READY；还必须按 `a` 才开始发送。空格暂停，`q` 或 Esc 停止。当前保存的配置是第三轮真机参数：完整模型关节范围、30 Hz、速度倍率 6、单周期最大步进 5%、平滑系数 0.25；丢手超过 0.25 秒立即停止写入。早期 8% 工作范围、1% 步进属于历史试验，不代表当前配置。

## 当前六项阶段状态

1. 模型登记与10轴顺序：已实现。
2. 连续重定向：已实现基础版本。
3. 被动关节耦合：已实现 MJCF 多项式版本。
4. 离线预览：已实现，不发命令。
5. 动作标定采集：已实现；保存了 427 条样本和版本 4 标定配置，换人后需重新检查或标定。
6. 真机控制：已完成现场跟随试验并保留累计日志；尚缺跟踪误差、端到端延迟和长时间稳定性量化验收，详见 [最新工作总结](docs/工作总结_单视觉项目.md)。

## 配置

编辑 `config/vision.json` 可以修改摄像头编号、分辨率、帧率、检测阈值、识别阈值和日志路径。默认使用 `/dev/video0` 对应的 camera index 0，分辨率为 640×480，目标帧率为 30 FPS。

命令行可临时覆盖摄像头：

```bash
bash scripts/run.sh --camera 0
```

## 重建环境

```bash
bash scripts/setup_env.sh
```

脚本使用系统 Python 3.10，在本目录 `.venv` 中安装固定兼容版本。环境脚本从同仓库 `../o10_usb_phase1/sdk/` 安装官方 SDK wheel；模型路径引用同仓库 `../o10_single_tactile/models/`。请保留四个子项目的兄弟目录关系。
