# OmniHand O10 灵巧手二次开发

本仓库按“方案与硬件评估、单视觉项目、单触觉项目、触觉相关资料”整理项目代码、官方 SDK、模型、交接文档、测试原始数据和生成图片。归档日期：2026-10-27。主要实测与文档形成于 2026 年 9 月。

## 先看什么

| 项目话题 | 内容与入口 | 当前阶段 |
| --- | --- | --- |
| 方案与硬件评估 | [左右手评估、阶段工作文档](docs/hardware/README.md) | USB 状态与频率实测；右手拇指触觉受压/释放已验证，CANFD 尚未验证 |
| USB 测试与交接 | [测试包](projects/o10_usb_test_bundle/README.md) · [完整交接文档](projects/o10_usb_test_bundle/USB直连O10测试_工作交接文档.md) | 官方只读 demo、预检、频率测试与早期视觉/触觉原型 |
| 单视觉项目 | [代码与运行入口](projects/o10_single_vision/README.md) · [最新工作总结](projects/o10_single_vision/docs/工作总结_单视觉项目.md) | 摄像头 → 重定向 → MuJoCo → O10 真机链路已打通；量化验收待补充 |
| 单触觉项目 | [项目说明](projects/o10_single_tactile/README.md) · [证据与路线](projects/o10_single_tactile/docs/DATA_REVIEW.md) | 只读触觉链路与基线数据已验证；自动抓取、接触停止和持握闭环尚未实现 |
| 触觉相关资料 | [阅读与方法指南](docs/references/触觉相关资料.md) · [Word 原文](docs/references/触觉相关资料.docx) | 已查阅资料、适用范围及实验建议；引用外部项目不代表完成复现 |

完整文件入口见 [文档索引](docs/README.md)，数据字段、样本数和实验解释见 [测试数据说明](docs/data/README.md)。

## 仓库结构

```text
.
├── projects/
│   ├── o10_usb_phase1/       # USB 只读监测、原始 JSONL、评估、独立 SDK
│   ├── o10_usb_test_bundle/  # 迁移交接、官方 demo 调用、早期原型
│   ├── o10_single_vision/    # 单视觉代码、配置、标定、实机日志、报告和图片
│   └── o10_single_tactile/   # 触觉证据、原始采集、官方原版 SDK 和模型
├── docs/
│   ├── hardware/            # 硬件评估与阶段文档入口
│   ├── data/                # 数据说明、逐文件统计、校验清单
│   ├── references/          # 触觉资料 Markdown / Word
│   └── archive/             # 来源映射、排除项和发布副本调整记录
└── THIRD_PARTY_NOTICES.md
```

四个子项目保留原有内部目录和兄弟目录关系。两份 SDK 有少量差异，分别保留以还原各项目状态；Git 会复用相同内容的对象。SDK 保留 Linux x64/aarch64 的库和 wheel、Windows 示例与其余库、demo 和 API 文档，模型含 URDF、MJCF 和网格。Windows 云通信 DLL 及包含它的 wheel 因内嵌私钥未公开，详见 [排除说明](docs/archive/README.md#排除内容)。

## 获取与离线检查

```bash
git clone https://github.com/chc1113/omnihand-o10-development.git
cd omnihand-o10-development
# Linux x86_64 / Python 3.10 是单视觉项目现有脚本的目标环境
cd projects/o10_single_vision
bash scripts/setup_env.sh
.venv/bin/python scripts/validate_model.py
.venv/bin/python scripts/test_retargeting.py
.venv/bin/python scripts/verify_official_gestures.py
```

环境目录和缓存不随仓库分发，由脚本重建。安装需要网络及 Python 3.10 的 venv/pip 支持。视觉环境使用固定版本的 NumPy、OpenCV、MediaPipe、MuJoCo 和仓库内 SDK 1.1.5 wheel。模型配置中的相对路径以 `projects/o10_single_vision` 为工作目录，因此直接运行 Python 脚本前也应进入该目录。

## 运行入口

- 视觉识别：在单视觉目录执行 `bash scripts/run.sh`。
- 摄像头到虚拟手：`bash scripts/run_sim.sh`；仅模型预览用 `bash scripts/run_sim.sh --no-camera`。
- 真机只读探测：`bash scripts/run_real.sh --probe-only`。
- 真机跟随：完成供电、场地检查、个人标定与仿真方向确认后，执行 `bash scripts/run_real.sh --arm REAL_HAND`，连续识别右手后按 `a` 启用；空格暂停，`q`/Esc 退出。
- USB 预检与官方只读例程：按 [交接包 README](projects/o10_usb_test_bundle/README.md) 操作；SDK 参数可指向本仓库的 `projects/o10_usb_phase1/sdk/agillink_omnihand_sdk-main`。
- 官方 SDK 新手流程：[USB 左手/右手上手指南](projects/o10_usb_phase1/sdk/agillink_omnihand_sdk-main/README_zh_cn.md)。

O10 需要独立 24 V 电源，USB 用于通信。当前真机配置为完整模型范围、30 Hz、速度倍率 6、每周期最大步进 5%；操作前应阅读 [最新工作总结中的真机控制现状](projects/o10_single_vision/docs/工作总结_单视觉项目.md)。不应将历史低幅试验的限制当作当前参数。

## 数据和结论边界

原始记录保留在各项目 `records/`、`logs/`、`data/` 中，Word 文档和图片按原字节保存。USB 的 `cycle` 行是采集周期，末行 `summary` 是汇总，不应计为额外样本。真机日志是多次运行累计记录，历史报告中的样本数是当时快照；逐文件统计以本仓库 [数据目录](docs/data/catalog.csv) 为准。

右手 USB 降采样触觉支持每指 16 点、掌心/手背各 25 点；Raw 高分辨率接口在 USB 后端不可用。现有压力实验主要覆盖右拇指，尚未完成全区域力标定；SDK 的触觉读数不能直接视作经独立载荷标定的精确力。视觉项目已有实机跟随，单触觉与视触觉融合抓取仍有待开发。

本次归档只执行文件完整性与离线检查，没有重新执行硬件动作或采集新硬件数据。历史 Word/Markdown 中保留的本机路径和设备标识用于记录当时环境；运行本仓库请优先采用本页与各项目当前 README。

## 来源与归档

[归档说明](docs/archive/README.md) 列出来源、发布调整和排除内容；[SHA-256 清单](docs/archive/SHA256SUMS) 可核对上传文件。[第三方声明](THIRD_PARTY_NOTICES.md) 保留 SDK 和模型的授权信息，不为混合仓库统一套用新的许可证。
