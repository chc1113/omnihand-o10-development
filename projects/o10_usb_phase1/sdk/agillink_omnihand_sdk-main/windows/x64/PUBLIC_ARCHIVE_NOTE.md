# Windows SDK 公开归档说明

公开副本排除了 `cpp/bin/kerneldlls/ZlgCloud.dll` 和 `python/` 下 5 个 Windows wheel（Python 3.10–3.14）。这些 wheel 均包含同一个内嵌 PEM 私钥的厂商云通信 DLL。未修改或重打包其余官方二进制。

Linux x64/aarch64 库及 wheel、Windows 示例源码和其他库仍保留。需要完整 Windows SDK 时，请从厂商提供的官方 SDK 下载渠道获取。原始文件哈希、排除原因与项目来源见仓库根目录 `docs/archive/`；本机原件未删除。
