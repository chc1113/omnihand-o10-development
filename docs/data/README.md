# 测试数据与生成文件说明

本目录解释各子项目中保留的原始数据；数据本体仍在原项目目录。逐文件大小、SHA-256、样本数和时间范围见 [catalog.csv](catalog.csv)，区域触觉统计、标定姿态分布和非空回读数见 [catalog.json](catalog.json)。统计依据本次归档文件重新解析，不包含新增硬件采集。

## 数据清单

USB 的采集周期 `cycle` 与末行汇总 `summary` 分开统计。`actual_poll_hz` 是采集循环频率，不是传感器内部扫描频率。

| 文件 | 周期/记录 | 汇总行 | 说明 |
| --- | ---: | ---: | --- |
| [live_idle_full_10hz_15s.jsonl](../../projects/o10_single_tactile/records/live_idle_full_10hz_15s.jsonl) | 150 | 1 | 2026-09-18 右手空载基线 |
| [calibration_samples.jsonl](../../projects/o10_single_vision/data/calibration_samples.jsonl) | 427 | 0 | 个人标定样本；不是通用人群训练集 |
| [hand_actions.jsonl](../../projects/o10_single_vision/logs/hand_actions.jsonl) | 23 | 0 | 早期动作识别事件记录 |
| [real_hand_session.jsonl](../../projects/o10_single_vision/logs/real_hand_session.jsonl) | 5872 | 0 | 多次真机跟随运行累计；不等于连续单次试验 |
| [full_10hz.jsonl](../../projects/o10_usb_phase1/records/full_10hz.jsonl) | 100 | 1 | 早期全量读取 10 Hz |
| [full_10hz_5min.jsonl](../../projects/o10_usb_phase1/records/full_10hz_5min.jsonl) | 3000 | 1 | 早期全量读取长测 |
| [full_2hz.jsonl](../../projects/o10_usb_phase1/records/full_2hz.jsonl) | 12 | 1 | 早期全量读取 2 Hz |
| [full_5hz.jsonl](../../projects/o10_usb_phase1/records/full_5hz.jsonl) | 50 | 1 | 早期全量读取 5 Hz |
| [left_full_no_tactile_10hz_5min.jsonl](../../projects/o10_usb_phase1/records/left_full_no_tactile_10hz_5min.jsonl) | 3000 | 1 | 左手全状态读取，不请求触觉 |
| [left_full_with_tactile_probe.jsonl](../../projects/o10_usb_phase1/records/left_full_with_tactile_probe.jsonl) | 100 | 1 | 左手触觉只读探测；不能由零值推定压力响应已通过 |
| [left_positions_50hz_5min.jsonl](../../projects/o10_usb_phase1/records/left_positions_50hz_5min.jsonl) | 15000 | 1 | 左手位置长测 |
| [positions_20hz.jsonl](../../projects/o10_usb_phase1/records/positions_20hz.jsonl) | 200 | 1 | 早期位置读取 20 Hz |
| [positions_50hz.jsonl](../../projects/o10_usb_phase1/records/positions_50hz.jsonl) | 500 | 1 | 早期位置读取 50 Hz |
| [positions_50hz_5min.jsonl](../../projects/o10_usb_phase1/records/positions_50hz_5min.jsonl) | 15000 | 1 | 早期位置读取长测 |
| [positions_5hz.jsonl](../../projects/o10_usb_phase1/records/positions_5hz.jsonl) | 40 | 1 | 早期位置读取 5 Hz |
| [right_full_10hz_5min.jsonl](../../projects/o10_usb_phase1/records/right_full_10hz_5min.jsonl) | 3000 | 1 | 右手空载全状态及降采样触觉基线 |
| [right_positions_50hz_5min.jsonl](../../projects/o10_usb_phase1/records/right_positions_50hz_5min.jsonl) | 15000 | 1 | 右手位置长测 |
| [right_thumb_pressure_10hz_30s.jsonl](../../projects/o10_usb_phase1/records/right_thumb_pressure_10hz_30s.jsonl) | 300 | 1 | 右拇指受压；其余区域未施压 |
| [right_thumb_release_10hz_10s.jsonl](../../projects/o10_usb_phase1/records/right_thumb_release_10hz_10s.jsonl) | 100 | 1 | 右拇指松开回零 |
| [wire_full.jsonl](../../projects/o10_usb_phase1/records/wire_full.jsonl) | 1 | 1 | 早期全量协议抓取样例，非长测 |
| [wire_positions.jsonl](../../projects/o10_usb_phase1/records/wire_positions.jsonl) | 2 | 1 | 早期位置协议抓取样例，非长测 |

早期没有 `left_`/`right_` 前缀的文件保留原名，不仅凭文件名推断手侧；以 [左右手评估](../hardware/README.md) 和交接文档为准。

## JSONL 字段和单位

每个非空行是一个独立 JSON 对象，不能把整个 JSONL 当作单一 JSON 数组读取。`wall_time` 是 Unix 秒时间戳，转换时应显式指定时区；脚本调用耗时和整周期耗时单位为毫秒，`started_monotonic_ns` 为本机单调时钟纳秒，不能跨进程作为绝对时间对齐。

| 数据类型 | 字段 | 含义 |
| --- | --- | --- |
| USB 周期 | `type=cycle`, `cycle_index`, `cycle_duration_ms`, `calls` | 一个轮询周期及逐接口调用 |
| USB 调用 | `name`, `duration_ms`, `ok`, `error`, `value`, `length` | 调用结果、耗时、返回值与长度；空值和错误不能当作有效零值 |
| USB 汇总 | `type=summary`, `cycles`, `elapsed_s`, `actual_poll_hz`, `calls` | 周期数、频率、各接口延迟及失败/空返回统计 |
| 视觉标定 | `pose`, `coordinate_source`, `handedness_score`, `points`, `features` | 21×3 手部关键点、坐标来源和 11 个映射特征；姿态和置信度均非力学真值 |
| 动作事件 | `action`, `handedness`, `bends`, `pinch_distance` | 早期视觉动作分类及归一化特征 |
| 实机跟随 | `command`, `measured`, `tracking_score` | 按模型主动关节顺序排列的 10 个目标/实测关节角（弧度），以及视觉置信度 |

USB `positions` 是 SDK 执行器位置值，不能直接当作弧度；`angles` 是关节角。电流、温度、错误码需结合所附 SDK 的接口定义和设备版本解释。降采样触觉每指 16 点、掌心和手背各 25 点；SDK 标称触觉单位/读数未经本项目独立载荷标定，不能直接视为精确的牛顿力。

当前真机命令目标频率为 30 Hz，回读为 2 Hz，因此 `measured=null` 是未在该行采样回读的正常情况，不能据此算作控制失败。实际日志跨多次运行累积，不应将相邻时间间隔直接当作连续稳定运行或把 `tracking_score` 当作关节跟踪误差。关节顺序见 [模型配置](../../projects/o10_single_vision/config/omnihand_right_model.json)。

## 可以支持的结论

- 右手空载基线 3000 周期拇指全零；受压 300/300 周期非零，单点峰值 150、区域总和最大 887；释放后 100/100 周期全零。
- 单触觉项目最近的空载记录为 150 周期，约 9.99995 Hz，7 个区域返回长度正确且全零；这是历史证据的复核，本次没有重新触碰硬件。
- 当前尚未完成各区域载荷标定、左右手全面施压验证、接触停止/持握闭环和视触觉融合抓取。USB Raw 返回空数组属于后端不支持，不能与降采样空载零值混淆。

## 标定与历史快照

有效标定保存在 [config/calibration_right.json](../../projects/o10_single_vision/config/calibration_right.json)（版本 4），对应 427 条个人样本。换人、相机位置或成像条件变化后应重新检查或采集。

[calibration_right_v1_wrong_anchors_20260916.json](../../projects/o10_single_vision/data/calibration_right_v1_wrong_anchors_20260916.json) 是错误锚点的旧版标定，只为追溯保留，不能加载替换当前配置。最新工作总结形成时记录 2727 条命令；本次归档的累计 `real_hand_session.jsonl` 为 5872 条，两者对应不同时间快照，原报告未改写。

## 已生成图片

以下图片保留原字节，用于模型关节扫描、拇指方向、标定对比与官方手势核对；不能作为硬件跟踪精度的测量结果。

- [a0.png](../../projects/o10_single_vision/data/a0.png)
- [a1.png](../../projects/o10_single_vision/data/a1.png)
- [a2.png](../../projects/o10_single_vision/data/a2.png)
- [joint_sweep.png](../../projects/o10_single_vision/data/joint_sweep.png)
- [official_paper_ok.png](../../projects/o10_single_vision/data/official_paper_ok.png)
- [thumb_abad_choice.png](../../projects/o10_single_vision/data/thumb_abad_choice.png)
- [thumb_fist_grid.png](../../projects/o10_single_vision/data/thumb_fist_grid.png)
- [thumb_fist_grid_back.png](../../projects/o10_single_vision/data/thumb_fist_grid_back.png)
- [thumb_fist_grid_outside.png](../../projects/o10_single_vision/data/thumb_fist_grid_outside.png)
- [v4_corrected_screenshot_poses.png](../../projects/o10_single_vision/data/v4_corrected_screenshot_poses.png)
- [v4_predicted_screenshot_poses.png](../../projects/o10_single_vision/data/v4_predicted_screenshot_poses.png)
