# 归档离线复核记录

日期：2026-10-27。检查对象是本仓库的发布副本；本次没有打开相机、连接串口/CAN、发送动作命令或追加实测数据。

## 已执行检查

| 检查 | 结果 |
| --- | --- |
| 来源与发布文件 SHA-256 | 2133 个保留来源条目均可对应；8 个文本文件有已记录的发布调整，其余一致 |
| 原始数据与文档 | 21 个 JSONL、4 个 Word、12 个 PNG 与来源字节一致（其中 11 个 PNG 为单视觉实验图片） |
| 数据格式 | 21 个 JSONL 全部逐行解析成功；18 个 USB 文件的周期数与末行 summary 一致 |
| Python 语法 | 26 个项目 Python 文件通过 AST 解析；不包含第三方 SDK/模型脚本 |
| Shell 语法 | 10 个项目 shell 脚本通过 `bash -n`；不执行脚本 |
| 模型元数据 | 10 个主动关节顺序与 MJCF actuators 一致，URDF 含对应关节 |
| 重定向与限幅 | `scripts/test_retargeting.py` 通过：手势、特征变换、方向和安全限幅断言 |
| 官方手势 | `scripts/verify_official_gestures.py` 通过：PAPER / OK / NUM1 / NUM2 / NUM3 / NUM4 / NUM6 / NUM8 |
| MuJoCo 无界面加载 | 仓库内模型成功加载：10 个执行器、16 个关节、21 个网格；中间姿态前向计算为有限值 |
| SDK 符号链接 | 48 个相对链接均可解析且目标位于仓库内 |
| 发布调整可追溯 | `git apply --reverse --check docs/archive/portability.patch` 通过 |
| 第三方 SDK 对比 | 两份 SDK 保持 2 个内容差异和 1 个单侧新增文件，见归档说明 |
| 凭据检查 | 文件及 24 个保留 ZIP 容器（含 wheel/Word）的全部成员按强凭据模式扫描，未再发现匹配；含私钥的 12 个 Windows 厂商文件已排除 |

完整性清单覆盖本次发布文件，在仓库根目录运行 `sha256sum --quiet -c docs/archive/SHA256SUMS` 复核。主索引与本次调整的 Markdown 链接按本地目标存在性检查。

## 检查环境与命令

复用原机已经安装的单视觉 Python 3.10.12 环境，NumPy 1.26.4、OpenCV 4.11.0、MediaPipe 0.10.21、MuJoCo 3.10.0、OmniHand SDK 1.1.5。MuJoCo 在原机共享目录，因此本次离线复核临时通过 `PYTHONPATH` 注入；仓库运行脚本已改为由项目 requirements 安装 MuJoCo。

```bash
cd projects/o10_single_vision
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/chc/.local/lib/python3.10/site-packages
/home/chc/O10/o10_single_vision/.venv/bin/python scripts/test_retargeting.py
/home/chc/O10/o10_single_vision/.venv/bin/python scripts/validate_model.py
/home/chc/O10/o10_single_vision/.venv/bin/python scripts/verify_official_gestures.py
```

这些绝对路径仅记录归档机器上实际使用的环境。其他机器应先运行 `bash scripts/setup_env.sh`，再使用 `.venv/bin/python` 执行检查。

## 验证边界

此次未新建全新虚拟环境进行网络安装，也未在其他操作系统/CPU 平台执行 SDK；Windows 完整安装包需要自行从厂商获取。没有重新验证相机画面、硬件动作方向、长期连续稳定性或跟踪精度。文档中的硬件结论来自随仓库保留的历史实验记录，不能将离线通过等同于重新完成现场验收。
