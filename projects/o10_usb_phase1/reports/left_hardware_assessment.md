# O10 当前左手硬件评估

测试对象：当前接入的左手 O10，USB CDC 设备
`/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_386833633335-if00`。
本轮没有发送位置、角度、电流阈值、功率或控制模式写入命令。

## 结论

- USB 位置反馈可行：5 分钟、50 Hz，15000/15000 周期成功，实际 `49.99999 Hz`；单次读取平均 `0.444 ms`，P99 `0.742 ms`，最大 `0.983 ms`。
- USB 状态反馈可行：位置、角度、电流、温度、错误均可读取；左手全量（不含触觉）10 Hz 长测记录在 `records/left_full_no_tactile_10hz_5min.jsonl`。
- 当前左手不能证明有有效压力传感器：降采样触觉接口虽然返回固定长度，但 20 秒/100 周期中手指和掌心全部为 0，手背只有 99 个值为 1 的单点噪声；原始触觉接口明确返回空数据。
- USB 触觉闭环不可用：官方 ROS2 节点启动触觉流时报告 `GetAllTactileSensorDataRaw is not supported by USB communication`，没有有效 `tactile_states` 消息。
- 摄像头可用：`/dev/video0` 为 HD Webcam，支持 640x480@30（JPEG/YUY2）和最高 1280x720@10；640x480 JPEG 采集 300 帧耗时约 10.5 s，YUY2 640x480 采集 150 帧耗时约 5.53 s，约 27 fps。`/dev/video1` 不是采集节点。
- 当前系统没有 `can0`/`can1` 或 USB-CANFD 设备，因此 CANFD 触觉链路尚未验证。

## 触觉证据

Python SDK 只读探针结果：

- `get_tactile_sensor_data(Finger.THUMB)`：16 点全 0；其余手指同样为 16 点，掌心/手背为 25 点。
- `get_tactile_sensor_data_raw(Finger.THUMB)`：`sensor_id=Finger.???`，`data=[]`。
- `get_all_tactile_sensor_data_raw()`：空列表。

因此当前只能说 O10 USB 协议保留了降采样触觉查询接口，不能把返回的零数组当作“有压力传感器但未受力”。要确认右手带压力传感器，需接入右手并在同样的 USB/CANFD 两条路径上比较非零响应；建议先用 CANFD，因为官方 ROS2/SDK 明确将原始触觉数据标为 CANFD 多帧能力。

## ROS2 只读路径

项目配置：`config/omnihand_2025_usb_readonly.yaml`，当前已切换为左手。

- 左手节点 USB 初始化成功，电流/温度/错误读取请求可以返回 10 元素状态。
- 位置状态由官方节点的 `joint_cmd` 触发；本轮未发布该控制话题，因此没有做电机动作或位置闭环测试。
- 触觉 `tactile_cmd` 只能启动尝试，USB 下会返回“不支持原始触觉”的错误。

## 右手接入后的复测要求

右手带压力传感器接入后，不要沿用本轮记录。按左手相同顺序新建 `right_*` 记录：设备信息、位置 50 Hz 长测、全量状态 10 Hz 长测、降采样触觉短测、原始触觉/CANFD 测试、ROS2 触觉话题帧率和非零响应。只有在施加已知轻微接触并看到稳定非零阵列后，才判定“可以实现触觉”。
