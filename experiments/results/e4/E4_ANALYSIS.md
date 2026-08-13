# E4 Final Analysis

## Offline Backlog Scalability of Dual-Cloud Recovery

E4 evaluated the effect of historical offline telemetry backlog size on recovery behaviour after real network restoration.

Three backlog levels were evaluated: **10, 30, and 60 records**, with three formal independent sessions per workload level.

A total of **9 formal trials** were therefore included in the analysis.

## 1. Workload-Level Results

| Backlog | Azure Recovery (s) | ThingsBoard Recovery (s) | Azure Throughput (records/s) | ThingsBoard Throughput (records/s) |
|---:|---:|---:|---:|---:|
| 10 | 40.073 ± 3.261 | 29.789 ± 2.716 | 0.2506 ± 0.0198 | 0.3375 ± 0.0298 |
| 30 | 65.928 ± 15.566 | 52.027 ± 12.626 | 0.4709 ± 0.1009 | 0.5979 ± 0.1324 |
| 60 | 85.360 ± 2.497 | 77.446 ± 2.423 | 0.7033 ± 0.0209 | 0.7752 ± 0.0247 |

## 2. Recovery-Time Variability

- Backlog 10: Azure recovery CV = **8.14%**, ThingsBoard recovery CV = **9.12%**.
- Backlog 30: Azure recovery CV = **23.61%**, ThingsBoard recovery CV = **24.27%**.
- Backlog 60: Azure recovery CV = **2.93%**, ThingsBoard recovery CV = **3.13%**.

## 3. Reliability

- Formal E4 trials completed: **9**
- Successful historical-backlog recoveries: **9/9**
- Observed recovery success rate: **100%**

## 4. Scaling Behaviour

Mean historical-backlog recovery time increased as workload size increased from 10 to 30 and then 60 records.

However, recovery time increased substantially less than proportionally to the six-fold growth in backlog size from 10 to 60 records.

At the same time, effective historical backfill throughput increased with backlog size. This behaviour is consistent with the presence of fixed network-reconnection and synchronization overheads that are amortized across larger historical workloads.

## 5. Descriptive Linear Models

The following models are descriptive workload-level fits and should not be interpreted as proof of general linear scalability.

### Azure Recovery

T(N) = 34.2749 + 0.8854 N

R² = 0.9618

### ThingsBoard Recovery

T(N) = 21.5942 + 0.9448 N

R² = 0.9942

## 6. Cross-Platform Pattern

- Azure showed earlier first recovery progress in **9/9** formal trials.
- ThingsBoard completed full historical recovery faster in **9/9** formal trials.
- ThingsBoard achieved higher effective backfill throughput in **9/9** formal trials.

## 7. Interpretation

The E4 results provide evidence that the proposed SQLite-based store-and-forward architecture can recover historical telemetry across the tested 10-, 30-, and 60-record workload levels while the edge application continues operating.

The observed increase in recovery time with workload size indicates a measurable backlog-dependent cost. However, effective throughput also increased as the backlog became larger, suggesting that fixed reconnection and synchronization overhead represents a substantial fraction of total recovery time for small workloads.

Across the tested prototype configuration, Azure generally initiated historical recovery slightly earlier, whereas ThingsBoard completed the frozen historical backlog sooner and achieved higher effective backfill throughput.

## 8. Limitations

Only three backlog levels were evaluated, and each level contained three formal repetitions.

The experiment therefore characterizes recovery behaviour only within the tested prototype and workload range. It does not establish general performance characteristics of Azure IoT Hub or ThingsBoard.

The reported throughput is a system-level effective backfill metric and includes network reconnection, cloud communication, local worker scheduling, and SQLite state-update overhead.

## 9. E4 Conclusion

**E4 RESULT: PASS**

All nine formal trials successfully recovered the complete frozen historical backlog after network restoration.

Recovery time increased with backlog size over the tested range, while effective historical backfill throughput also increased, indicating that fixed recovery overhead is progressively amortized across larger queued workloads.
