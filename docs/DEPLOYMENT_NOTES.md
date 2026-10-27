# 部署与未收录内容说明

更新日期：2026-10-27。适用于从本仓库拉取项目后重建环境、查看历史数据及部署 O10。先按所用系统阅读本页，再进入对应子项目 README。

## 先确认 SDK 版本和文件状态

本项目使用官方 SDK **1.1.5**，来源为 [AgibotTech/agillink_omnihand_sdk 的固定提交](https://github.com/AgibotTech/agillink_omnihand_sdk/tree/c53ddfec190889e89f8a1ef39efc00f84ac706c3)。已逐项对比该提交的 993 个文件：两份 SDK 都没有缺失项；触觉副本全部一致，USB 副本保留项目的新手指南和 USB 配置，并新增 USB 权限规则。

此前未上传的两套 Windows 文件已全部补齐：每套含 `ZlgCloud.dll` 和 Python 3.10～3.14 的 5 个 wheel，共 12 个路径、6 种文件。原先的私钥扫描排除原因、此次确认的官方公开来源及文件哈希见 [补齐记录](archive/UPSTREAM_COMPARISON.md)。不再需要为这 12 个文件另行寻找下载来源。

核对时官方主分支为 SDK **1.1.10**。该版本增加或更改了库、示例、接口及文件布局，本仓库没有把它混入 1.1.5。需要升级时应作为独立迁移工作验证，不能仅复制新版缺少的路径并与旧库混装。

## 当前未上传的内容及影响

以下是 [当前排除清单](archive/exclusions.json) 的全部 13 个路径；路径以 `projects/` 为起点。缓存目录按目录根记录，不逐个列出 `.pyc`。

| 未收录路径 | 原因和部署处理 |
| --- | --- |
| `o10_usb_phase1/.venv` | 原机 Python 环境；运行该项目 `setup_env.sh` 重建 |
| `o10_usb_phase1/.phase1_env` | 含原机 SDK/wheel 位置；运行 `setup_env.sh` 按新位置生成 |
| `o10_usb_test_bundle/.venv.incomplete-20260914` | 历史未完成环境；不恢复它，运行测试包 `setup_env.sh` 创建新的 `.venv` |
| `o10_single_vision/.venv` | 原机视觉环境；运行 `scripts/setup_env.sh` 重建 |
| `o10_usb_phase1/scripts/__pycache__` | Python 字节码缓存，运行时自动生成 |
| `o10_usb_phase1/sdk/agillink_omnihand_sdk-main/linux/x64/ros2/humble/lib/python3.10/site-packages/omnihand_2025_node_msgs/__pycache__` | ROS2 Python 缓存，运行时自动生成 |
| `o10_usb_phase1/sdk/agillink_omnihand_sdk-main/linux/x64/ros2/humble/lib/python3.10/site-packages/omnihand_2025_node_msgs/msg/__pycache__` | ROS2 消息缓存，运行时自动生成 |
| `o10_usb_phase1/sdk/agillink_omnihand_sdk-main/linux/x64/ros2/humble/share/omnihand_node/launch/__pycache__` | ROS2 启动脚本缓存，运行时自动生成 |
| `o10_usb_test_bundle/projects/tactile_interaction/__pycache__` | Python 字节码缓存，运行时自动生成 |
| `o10_usb_test_bundle/projects/vision_tracking/__pycache__` | Python 字节码缓存，运行时自动生成 |
| `o10_usb_test_bundle/scripts/__pycache__` | Python 字节码缓存，运行时自动生成 |
| `o10_single_vision/scripts/__pycache__` | Python 字节码缓存，运行时自动生成 |
| `o10_single_vision/src/__pycache__` | Python 字节码缓存，运行时自动生成 |

这些内容不承担项目算法、模型或原始数据的保存功能，但虚拟环境缺失意味着克隆后需要安装依赖。仓库也不分发系统 Python、USB/CAN 驱动、相机驱动和系统权限配置。后续生成的 `.venv_config`、`.env`、缓存等仍由 `.gitignore` 忽略，应在部署机配置。

最初下载的 SDK/模型 ZIP 不重复上传，解压后的 SDK、URDF、MJCF 和网格已收录；原压缩包名称与哈希见 [SOURCES.md](../projects/o10_single_tactile/SOURCES.md)。参考资料原件已放入 `docs/references/`，不再在根目录重复发布。仓库不包含原始聊天记录。

## Linux x86_64：重建现有项目环境

现有单视觉脚本的目标是 Linux x86_64、Python 3.10。需要系统已提供 Python 3.10、该解释器可用的 pip/venv，以及下载 Python 依赖所需的网络。请完整克隆仓库，保留四个子项目的兄弟目录关系；视觉项目会读取 USB 项目的 SDK 和触觉项目的模型。

```bash
git clone https://github.com/chc1113/omnihand-o10-development.git
cd omnihand-o10-development
sha256sum --quiet -c docs/archive/SHA256SUMS

cd projects/o10_single_vision
bash scripts/setup_env.sh
.venv/bin/python -c 'import omnihand, cv2, mediapipe, numpy, mujoco; print("依赖导入成功")'
.venv/bin/python scripts/validate_model.py
.venv/bin/python scripts/test_retargeting.py
.venv/bin/python scripts/verify_official_gestures.py
```

上述检查不连接实体手。Python 脚本应在单视觉项目目录运行，以正确解析配置中的模型相对路径。安装脚本不会恢复原机已有的虚拟环境内容，而是根据 requirements 和仓库内 Linux SDK wheel 安装。

USB 只读阶段项目可在其目录执行 `PYTHON_BIN=/usr/bin/python3.10 bash setup_env.sh`，随后 `source env.sh`。USB 交接测试包可在其目录执行：

```bash
PYTHON_BIN=/usr/bin/python3.10 bash setup_env.sh ../o10_usb_phase1/sdk/agillink_omnihand_sdk-main
source env.sh ../o10_usb_phase1/sdk/agillink_omnihand_sdk-main
```

接实机前，应按 [USB 新手指南](../projects/o10_usb_phase1/sdk/agillink_omnihand_sdk-main/README_zh_cn.md) 确认独立 24 V 供电、USB 权限和新机器实际串口；设备名及序列号可能与历史文档不同。先执行单视觉项目的 `bash scripts/run_real.sh --probe-only` 做只读探测，再依 [最新工作总结](../projects/o10_single_vision/docs/工作总结_单视觉项目.md) 完成相机、个人标定、仿真方向和动作启用步骤。历史个人标定样本保留用于追溯，不保证适合其他操作者。

## Windows x64：SDK 已齐全，项目适配仍需验证

Windows SDK 所需的上述 DLL 和 5 个 wheel 现已收录。以仓库根目录、64 位 CPython 3.10 为例，可在 PowerShell 中创建独立环境并安装 wheel：

```powershell
py -3.10 -m venv .venv-windows
.\.venv-windows\Scripts\python.exe -m pip install .\projects\o10_usb_phase1\sdk\agillink_omnihand_sdk-main\windows\x64\python\omnihand-1.1.5-cp310-cp310-win_amd64.whl
.\.venv-windows\Scripts\python.exe -c "import omnihand; print(omnihand.__file__)"
```

其他 CPython 版本需要对应的 `cp311`～`cp314` wheel；项目视觉依赖另外受 requirements 的版本约束，不能由“SDK 有该 wheel”推导出全部视觉依赖都支持该 Python 版本。驱动、C++ 库和安装器说明见 [官方 Windows 文档](../projects/o10_usb_phase1/sdk/agillink_omnihand_sdk-main/windows/x64/README_zh_cn.md)。ROS2 和 SocketCAN 的此 SDK 支持仅限 Linux。

本项目的环境脚本和运行脚本采用 bash/Linux 路径，Windows 部署还需适配脚本、串口及依赖环境。本次没有在 Windows 执行上述命令或进行实机测试；文件完整不等于已完成 Windows 端部署验收。

## ARM、CANFD 与验证范围

Linux aarch64 SDK 也已保留，但现有单视觉安装脚本明确选择 x86_64 wheel；ARM 机器需选用 aarch64 SDK 并适配依赖，不能直接照搬该脚本。CANFD 库的文件完整性不等于本项目已验证 CANFD 实机通信。

本次补齐只核对文件与离线功能，不连接相机、不发送硬件命令，也没有在全新系统重新安装环境。已有测试数据、交接文档、模型和实验图片均保留。硬件证据、未实现的触觉闭环及离线验证范围见 [数据说明](data/README.md) 与 [VALIDATION.md](archive/VALIDATION.md)。
