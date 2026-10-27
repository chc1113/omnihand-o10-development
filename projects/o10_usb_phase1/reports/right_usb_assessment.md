# O10 当前右手 USB 评估

测试对象：单独接入的右手 O10，USB CDC 路径由 `env.sh` 自动发现。
本轮没有发送位置、角度、电流阈值、功率或控制模式写入命令。

## 结果

- 设备信息读取成功：O10、设备 ID 1、硬件版本 3.0.0、软件版本 1.2.7、10 个主动关节。
- USB 位置反馈：5 分钟、50 Hz，15000/15000 周期成功，实际 `49.99999 Hz`；位置调用 P99 `0.772 ms`，最大 `0.955 ms`。
- USB 全量状态/降采样触觉：5 分钟、10 Hz，3000/3000 周期成功，实际 `10.00000 Hz`；全周期平均约 `11.064 ms`，P99 `11.787 ms`，最大 `13.089 ms`；没有异常、空返回或断连。
- 右手降采样触觉接口返回正确长度：手指 16 点，掌心/手背 25 点。此前空载记录中 3000 组样本的全部点均为 0。
- 本次对大拇指指尖施加轻微压力时，30 秒、10 Hz、300 个周期中拇指区域 300/300 个周期均为非零；16 点阵列单周期最高值约 `150`，单周期示例为 `[2, 2, 80, 92, 145, 146, 132, 132, 66, 23, 0, 0, 0, 0, 0, 0]`。食指、中指、无名指、小拇指、掌心、手背在同一测试中保持全零。
- 松开拇指后，10 秒、10 Hz、100 个周期中拇指阵列 100/100 个周期全部回到 0，证明该降采样接口能随拇指压力变化；记录分别为 `records/right_thumb_pressure_10hz_30s.jsonl` 和 `records/right_thumb_release_10hz_10s.jsonl`。
- Python SDK 原始触觉接口仍返回空数据：`get_tactile_sensor_data_raw()` 的 `data=[]`，`get_all_tactile_sensor_data_raw()` 返回空列表，并打印 `not supported by USB communication`。
- ROS2 右手节点可以启动，电流状态请求可以返回；发布 `tactile_cmd` 后节点明确报告 `GetAllTactileSensorDataRaw is not supported by USB communication`，没有有效 `tactile_states`。

## 判断

1. 右手 USB 位置、角度、电流、温度、错误反馈链路可行。
2. 官方 ROS2 的原始触觉流不能通过 USB 实现，即使右手物理上带压力传感器。
3. USB 下的降采样 `get_tactile_sensor_data()` 已验证可以实现有限触觉：拇指受压时出现稳定的 16 点非零阵列，释放后回零。当前尚未对其他手指和掌心逐区域施压验证。
4. 原始高分辨率触觉和 ROS2 触觉流需要 CANFD 路径；当前没有 CANFD 硬件，因此该路径尚未验证。

记录：

- `records/right_positions_50hz_5min.jsonl`
- `records/right_full_10hz_5min.jsonl`
- `records/wire_full.jsonl`（早期设备帧示例）
