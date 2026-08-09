| 实验        | 要证明什么         | 核心指标                                |
| --------- | ------------- | ----------------------------------- |
| E1 边缘控制响应 | 高温发生后边缘端能快速动作 | Edge command latency                |
| E2 真实断网自治 | 没有云也能持续监测和控制  | Local continuity / data retention   |
| E3 网络恢复补传 | 离线数据不会丢失      | Recovery time / upload success rate |
| E4 双云独立性  | 一个云异常不能破坏整个系统 | Azure/TB independent recovery       |



Experiments/
├── edge_response_test.py    # E1 Baseline Edge Latency 构建了Baseline Experimental Dataset
├── edge_response_optimized_test.py # E1 Optimized Edge Latency    Optimized 实验程序,
├── formal/ # 正式实验
│   ├── baseline_latency_test.py    # 正式Baseline脚本
│   ├── optimized_latency_test.py   # 正式Optimized脚本
│   └── analyze_e1.py    # 生成正式E1汇总文件


实验分别跑：每次中间都有时间间隔，
Session 1
python -m experiments.formal.baseline_latency_test --session 1
python -m experiments.formal.optimized_latency_test --session 1
生成Session 1文件，并分析，见：result/formal/

Session 2调换顺序
python -m experiments.formal.optimized_latency_test --session 2
python -m experiments.formal.baseline_latency_test --session 2

Session 3 按照Session 1的顺序
python -m experiments.formal.baseline_latency_test --session 3
python -m experiments.formal.optimized_latency_test --session 3