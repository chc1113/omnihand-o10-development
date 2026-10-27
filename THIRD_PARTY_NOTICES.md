# 第三方来源与授权声明

## AGILINK OmniHand SDK 1.1.5

保留于 `projects/o10_usb_phase1/sdk/agillink_omnihand_sdk-main` 与 `projects/o10_single_tactile/sdk/agillink_omnihand_sdk-main`，含厂商的二进制库、Linux Python wheel、C++/Python/ROS2 示例及中英文文档。公开副本排除了内嵌私钥的 Windows ZlgCloud.dll 及包含它的 10 个 Windows wheel，详见 [归档说明](docs/archive/README.md#排除内容)。来源是项目当时使用的本地 SDK；原压缩包哈希与提交标识见 [SOURCES.md](projects/o10_single_tactile/SOURCES.md)。

SDK 自带英文 README 的 License 声明为：`Mulan PSL v2 - Copyright (c) 2025, Agibot Co., Ltd.`。本次整理保留原声明；提供的目录未见独立 LICENSE 正文，不补造授权文本。随 SDK 分发的其他库仍遵循各自已有声明。

USB 项目的 SDK 中文 README 包含本项目编写的新手指南，ROS2 USB 配置也有现场调整；单触觉项目保留另一份 SDK 状态。具体文件差异见 [归档说明](docs/archive/README.md)。

## OmniHand 模型

`projects/o10_single_tactile/models/omnihand_description-omnihandT2_1` 源自项目提供的 `1769933923166393.zip`，保留原 README、package.xml、URDF、MJCF、STL 及相关工程文件。`package.xml` 声明许可证为 `Apache-2.0`；未额外改写模型授权。

## Python 依赖与参考资料

NumPy、OpenCV、MediaPipe、MuJoCo 等依赖由 requirements 安装，未复制虚拟环境；各依赖遵循其自身许可证。触觉资料中的论文、项目与数据集以链接引用，不将“公开可见”自动解释为许可自由复制。

本仓库为混合项目归档，没有为全部原创材料与第三方内容统一指定新的开源许可证；公开可浏览不等于改变原有授权条件。
