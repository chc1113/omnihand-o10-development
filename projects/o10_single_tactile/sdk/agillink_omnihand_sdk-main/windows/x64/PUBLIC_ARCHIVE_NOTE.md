# Windows SDK 公开归档说明（已补齐）

2026-10-27：此前排除的 `cpp/bin/kerneldlls/ZlgCloud.dll` 和 `python/` 下 5 个 Windows wheel（Python 3.10–3.14）已原样补齐。

补齐来源为 [官方公开仓库的 SDK 1.1.5 原始提交](https://github.com/AgibotTech/agillink_omnihand_sdk/tree/c53ddfec190889e89f8a1ef39efc00f84ac706c3)。下载文件的 Git blob SHA-1 与官方树一致，SHA-256 与本机原件一致；未修改或重打包厂商二进制。先前检测到的厂商 DLL 内嵌 PEM 内容仍属于这些原始文件，文档不展开其正文。

本目录文件已齐全，但尚未在 Windows 执行安装或实机验证。项目自编写的 bash 脚本以 Linux 为目标；Windows 驱动和安装方式见 [官方 Windows 文档](README_zh_cn.md)。补齐记录和跨平台部署说明见仓库根目录 `docs/archive/UPSTREAM_COMPARISON.md`、`docs/DEPLOYMENT_NOTES.md`。
