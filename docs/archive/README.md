# 项目归档说明

归档日期：2026-10-27。此仓库是按项目研究主题组织的公开成果快照，含代码、文档、原始数据及生成文件，不包含聊天原始记录。现有本机工程未移动或改写，虚拟环境可在原处继续使用。

## 来源映射

| 本机来源 | 发布目录 | 内容 |
| --- | --- | --- |
| `/home/chc/O10/o10_usb_phase1` | `projects/o10_usb_phase1` | USB 只读监测、官方 SDK 新手指南、评估和测试数据 |
| `/home/chc/O10/o10_usb_test_bundle` | `projects/o10_usb_test_bundle` | USB 测试与迁移交接、三方向原型 |
| `/home/chc/O10/o10_single_vision` | `projects/o10_single_vision` | 单视觉控制链路、标定、日志、报告和图片 |
| `/home/chc/O10/o10_single_tactile` | `projects/o10_single_tactile` | 触觉资料分析、基线记录、SDK 与模型 |
| 项目文件夹中的 `触觉相关资料.md/.docx` | `docs/references` | 已查阅资料与阅读指南 |

[source_manifest.json](source_manifest.json) 对每个保留来源文件记录原始 SHA-256、发布 SHA-256 和是否调整。原路径只用于追溯；`source` 为相对于对应来源根目录的路径。符号链接的这两个哈希按链接文本计算，并单列 `link_target`。所有 Word、JSONL 和 PNG 均与本机源文件字节一致。

## 两份 SDK 的差异

USB 项目保留现场使用的 SDK，触觉项目保留其资料来源的 SDK 状态。两者除以下文件外内容一致；公开副本均应用下文相同的 Windows 排除项。

- USB SDK 的 `README_zh_cn.md` 含项目编写的 USB 新手指南。
- USB SDK 的 `linux/x64/ros2/humble/share/omnihand_node/config/omnihand_2025_node.yaml` 含现场 USB 配置。
- 仅 USB SDK 有 `linux/x64/99-omnihand-usb.rules`。

原厂 SDK 压缩包及模型压缩包的来源标识和哈希见 [单触觉 SOURCES.md](../../projects/o10_single_tactile/SOURCES.md)。SDK 和模型已有目录结构、二进制版本与许可证声明保留，参见 [第三方声明](../../THIRD_PARTY_NOTICES.md)。

## 发布副本调整

[changed_files.json](changed_files.json) 列出调整过的源文件，[portability.patch](portability.patch) 保存全部文本差异：

1. 单视觉模型配置指向仓库内触觉项目的模型；SDK 安装路径指向同仓库 USB 项目 wheel。
2. MuJoCo 3.10.0 加入单视觉依赖，移除运行脚本对原机共享 Python 目录的注入。
3. 单视觉 `.gitignore` 改为保留日志、标定样本和实验图片。
4. README 按最终保存的参数和实际完成状态更新；修正参考资料中的本机绝对 Markdown 链接。

没有改动控制算法、手势目标、真机控制参数或历史数据。历史正文、Word 和文档生成脚本中的原机路径用于追溯，未全部批量替换。直接运行单视觉 Python 脚本需先进入其项目目录。

如需检查原始文本，在临时副本中运行 `git apply --reverse --check docs/archive/portability.patch`，确认后才移除 `--check`。回退会恢复本机绝对路径和旧 README，因此不适合作为其他机器的运行配置；新增索引文档不属于该补丁。

## 排除内容

[exclusions.json](exclusions.json) 记录全部排除根目录/文件和原因。环境、缓存、失效环境路径不发布；通过环境脚本重建。原始测试数据、Word、图片、模型网格和 Linux SDK 库均保留。

两份 SDK 中的 `windows/x64/cpp/bin/kerneldlls/ZlgCloud.dll`，以及各自包含该 DLL 的 5 个 Windows Python wheel（3.10–3.14），共 12 个文件未纳入公开副本：检查发现厂商 DLL 内嵌完整 PEM 私钥。排除记录保留原文件 SHA-256，不复制密钥正文、不修改其他厂商库。需要完整 Windows SDK 时从厂商官方渠道获取；对应目录有 `PUBLIC_ARCHIVE_NOTE.md`。Linux USB 开发链路不依赖这些文件。

项目原目录和先前私有 SDK 备份仓库均未修改。本仓库是新的公开归档，不替换原私有备份。

## 校验与复核

在仓库根目录执行：

```bash
sha256sum --quiet -c docs/archive/SHA256SUMS
```

`SHA256SUMS` 覆盖全部发布文件，唯独不包含自身；按标准 `sha256sum` 行为，对符号链接校验其目标文件的内容。链接本身的文本另由来源映射校验；应使用 Git 克隆保留 SDK 的相对符号链接及可执行位。此清单验证此快照的完整性，后续修改文件后需要更新。

实际离线检查及环境限制见 [VALIDATION.md](VALIDATION.md)。全部硬件结论引用历史记录，本次归档没有开相机、串口、CAN 或执行实机运动。
