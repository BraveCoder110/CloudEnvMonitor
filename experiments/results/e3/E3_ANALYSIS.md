# E3 Final Analysis

## Dual-Cloud Recovery After Real Network Disconnection

E3 evaluates whether the edge system can preserve telemetry during a real network outage and automatically backfill historical records to both Azure IoT Hub and ThingsBoard after connectivity is restored.

## 1. Session Results

| Session | Azure Backlog | TB Backlog | Azure First Progress (s) | TB First Progress (s) | Azure Recovery (s) | TB Recovery (s) | Azure Throughput (records/s) | TB Throughput (records/s) | Result |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 23 | 24 | 7.441 | 8.647 | 48.692 | 37.228 | 0.4724 | 0.6447 | PASS |
| 2 | 22 | 22 | 14.489 | 15.297 | 53.375 | 41.899 | 0.4122 | 0.5251 | PASS |
| 3 | 22 | 22 | 8.858 | 9.662 | 46.906 | 36.445 | 0.4690 | 0.6037 | PASS |

## 2. Statistical Summary

| Metric | Platform | Mean | SD | CV (%) |
|---|---|---:|---:|---:|
| Initial backlog | Azure | 22.3333 | 0.5774 | 2.59 |
| Initial backlog | ThingsBoard | 22.6667 | 1.1547 | 5.09 |
| First-progress latency (s) | Azure | 10.2627 | 3.7281 | 36.33 |
| First-progress latency (s) | ThingsBoard | 11.2020 | 3.5825 | 31.98 |
| Recovery time (s) | Azure | 49.6577 | 3.3409 | 6.73 |
| Recovery time (s) | ThingsBoard | 38.5240 | 2.9489 | 7.65 |
| Effective throughput (records/s) | Azure | 0.4512 | 0.0338 | 7.50 |
| Effective throughput (records/s) | ThingsBoard | 0.5912 | 0.0608 | 10.28 |

## 3. Reliability

- Successful sessions: **3/3**
- Session success rate: **100.0%**
- All formal sessions required both historical cloud backlogs to meet the predefined minimum before recovery timing began.

## 4. Cross-Platform Recovery Pattern

- Azure showed the first historical backlog decrease earlier than ThingsBoard in **3/3** sessions.
- ThingsBoard completed historical backlog clearance faster than Azure in **3/3** sessions.
- ThingsBoard achieved higher effective backfill throughput in **3/3** sessions.

## 5. Mean Recovery Comparison

- Azure mean recovery time: **49.658 s**
- ThingsBoard mean recovery time: **38.524 s**
- Mean recovery-time difference: **11.134 s**
- ThingsBoard mean recovery time was **22.42% lower** than Azure in these three trials.

## 6. Mean Backfill Throughput

- Azure mean effective throughput: **0.4512 records/s**
- ThingsBoard mean effective throughput: **0.5912 records/s**
- Mean throughput difference: **0.1400 records/s**
- ThingsBoard mean effective throughput was **31.02% higher** than Azure in these three trials.

## 7. Interpretation

Across the three formal trials, the system successfully preserved telemetry locally during network disconnection and automatically recovered the frozen historical backlog for both cloud platforms after network restoration.

The repeated successful recovery demonstrates that edge operation and cloud communication are functionally decoupled: temporary cloud unavailability does not prevent local sensing, edge-state evaluation, actuator logic, or SQLite persistence.

A consistent cross-platform pattern was observed. Azure tended to show the first backlog decrease slightly earlier, whereas ThingsBoard completed historical backlog clearance faster and achieved higher effective backfill throughput in all three formal sessions.

Because the experiment contains three independent formal trials, these platform differences should be interpreted as empirical observations under the tested prototype configuration rather than as general performance claims about Azure IoT Hub or ThingsBoard.

## 8. E3 Conclusion

**E3 RESULT: PASS**

The prototype demonstrated successful dual-cloud recovery in all formal real-network-disconnection trials.
