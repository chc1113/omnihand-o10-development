# 官方仓库对比与补齐记录

核对日期：2026-10-27。官方仓库：[AgibotTech/agillink_omnihand_sdk](https://github.com/AgibotTech/agillink_omnihand_sdk)。本记录对应本仓库 SDK 1.1.5 的补齐，机器可读证据见 [upstream_comparison.json](upstream_comparison.json)。

## 采用的官方基准

项目原始 SDK ZIP 的提交标识为 [`c53ddfec190889e89f8a1ef39efc00f84ac706c3`](https://github.com/AgibotTech/agillink_omnihand_sdk/tree/c53ddfec190889e89f8a1ef39efc00f84ac706c3)，版本 1.1.5，依据见 [原始来源记录](../../projects/o10_single_tactile/SOURCES.md)。已通过 GitHub 递归 Git tree 获取该提交全部 993 个文件条目，返回结果没有截断。

逐项比较路径、Git blob SHA-1、文件模式（普通文件、可执行文件及符号链接）。补齐前两份项目 SDK 各缺少相同的 6 个条目；其余文件没有发现遗漏。

## 补齐的文件

下表路径相对于 `sdk/agillink_omnihand_sdk-main/`。每个文件均恢复到 `projects/o10_usb_phase1/` 和 `projects/o10_single_tactile/` 两份 SDK 中。

| 官方文件路径 | 文件大小（字节） | 状态 |
| --- | ---: | --- |
| `windows/x64/cpp/bin/kerneldlls/ZlgCloud.dll` | 660480 | 两份均已恢复 |
| `windows/x64/python/omnihand-1.1.5-cp310-cp310-win_amd64.whl` | 10390262 | 两份均已恢复 |
| `windows/x64/python/omnihand-1.1.5-cp311-cp311-win_amd64.whl` | 10391308 | 两份均已恢复 |
| `windows/x64/python/omnihand-1.1.5-cp312-cp312-win_amd64.whl` | 10392861 | 两份均已恢复 |
| `windows/x64/python/omnihand-1.1.5-cp313-cp313-win_amd64.whl` | 10392899 | 两份均已恢复 |
| `windows/x64/python/omnihand-1.1.5-cp314-cp314-win_amd64.whl` | 10393411 | 两份均已恢复 |

共 6 种文件、12 个仓库路径，每套 52,621,221 字节。Git 可复用两份相同文件的对象。

所有文件均从官方固定提交的 `raw.githubusercontent.com` 地址重新下载，验证下载大小及 Git blob SHA-1 与官方树一致，SHA-256 与本机原件及原排除记录一致。没有替换版本、修改 DLL 或重打包 wheel；具体下载 URL、完整哈希和恢复目标均写入 [JSON 记录](upstream_comparison.json)。

最初排除是因为 ZlgCloud.dll 内嵌完整 PEM 私钥，5 个 Windows wheel 也包含同一 DLL。本次依据用户要求，在确认这些文件由官方在该公开提交分发、且与本机原件一致后原样恢复。既有内嵌内容随厂商二进制保留，说明文档不复制密钥正文。当前排除清单已移除这 12 项；历史原因保留在 JSON 的 `restored_files` 中。

## 补齐后与原始提交的对比

| 项目 SDK 副本 | 与官方内容一致 | 保留的项目内容调整 | 缺失官方文件 | 项目新增文件 | 文件模式差异 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `o10_usb_phase1` | 991 | 2 | 0 | 2 | 0 |
| `o10_single_tactile` | 993 | 0 | 0 | 1 | 0 |

USB SDK 保留的两处内容调整为 `README_zh_cn.md`（项目 USB 新手指南）和 `linux/x64/ros2/humble/share/omnihand_node/config/omnihand_2025_node.yaml`（现场 USB 配置）。新增项为 USB 项目的 `linux/x64/99-omnihand-usb.rules`，以及两份 SDK 各自的 `windows/x64/PUBLIC_ARCHIVE_NOTE.md`。这些内容应与二次开发工程一起保留。

## 与官方最新主分支的区别

本次核对时，官方主分支为 [`1b552ea77c2d61adef327d179dc9f6b47405c628`](https://github.com/AgibotTech/agillink_omnihand_sdk/tree/1b552ea77c2d61adef327d179dc9f6b47405c628)，wheel 版本为 **1.1.10**，递归树共有 **4097** 个文件，结果没有截断。

最新主分支含新的设备支持、接口/服务文档、示例和编译产物，还更改了部分原有库与目录。当前每份 SDK 有 3306 个最新版本路径未收录；这些属于新旧版本之间的路径差异，不能视为本项目 SDK 1.1.5 漏传。两份 SDK 与最新版本的完整计数见 JSON 的 `after.latest`，与原始提交的完整核对见 `after.baseline`。

本次以原始提交补齐现有工程，不执行 SDK 1.1.10 升级。后续升级应整体评估 API、依赖、USB 行为及实机效果，再更新本项目的版本和验证记录，避免将 1.1.10 文件直接混入 1.1.5。

## 给部署者的结论

当前没有继续排除原始官方 SDK 的文件。仍未分发的原机环境和缓存，以及 Linux/Windows/ARM 的部署条件见 [部署与未收录内容说明](../DEPLOYMENT_NOTES.md)。此次文件核对没有在 Windows 安装 SDK，也没有重新执行实机动作；离线验证范围见 [VALIDATION.md](VALIDATION.md)。
