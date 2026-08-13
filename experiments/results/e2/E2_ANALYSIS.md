# E2 — Real Network Disconnection and Edge Autonomy

## Objective

E2 evaluated whether the Raspberry Pi edge system remained operational during a real network interruption.

The experiment examined local sensing, SQLite persistence, high-temperature state detection, LED warning, buzzer notification, infrared fan control, dual-cloud queue accumulation, and automatic synchronization after network restoration.

## Experimental configuration

- Raspberry Pi 4B
- DHT11 temperature sensor
- Red LED
- Active buzzer
- HX-53 infrared transmitter
- Three-level remote-controlled fan
- SQLite local telemetry persistence
- Microsoft Azure IoT Hub
- ThingsBoard telemetry platform
- High-temperature threshold: 29.0 °C
- Edge control continued while cloud communication ran asynchronously

## Session results

| Session | Records generated | Azure queue growth | ThingsBoard queue growth | Edge control | Backlog recovery | Result |
|---|---:|---:|---:|---|---|---|
| 1 | 25 | 22 | 22 | PASS | PASS | PASS |
| 2 | 26 | 24 | 22 | PASS | PASS | PASS |
| 3 | 23 | 21 | 20 | PASS | PASS | PASS |

## Overall result

- Formal sessions completed: 3
- Sessions passed: 3/3
- Session success rate: 100.0%
- Total records generated across PRE-to-OFFLINE_END windows: 74
- Mean records per session: 24.67

Across all successful sessions, the edge process continued generating SQLite telemetry records while cloud queues accumulated pending data.

A high-temperature state transition was successfully handled locally using the LED, one-shot buzzer alert, and level-2 fan control without requiring active cloud connectivity.

Following network restoration, Azure IoT Hub and ThingsBoard resumed transmission and the historical backlog was observed to drain to zero.

## Important interpretation

The Raspberry Pi and cloud services use an asynchronous producer-consumer architecture. Therefore, a recovered snapshot may contain one newly generated pending telemetry record even after the historical outage backlog has already been fully synchronized.

Recovery success is therefore defined by observing the historical backlog drain to zero in the runtime log, rather than requiring every instantaneous snapshot to remain permanently at 0/0.

## Sensor observations

Transient DHT11 read errors were observed in the experiment logs. These included checksum failures and incomplete buffers. The retry mechanism handled these transient failures without terminating the main edge-control loop.

## Limitation

The infrared-controlled fan is operated in an open-loop manner. The Raspberry Pi records successful command transmission but does not receive actuator-side acknowledgement confirming physical execution.

Physical actuator behaviour was therefore also observed manually during the formal experiments.

## Conclusion

E2 demonstrated that the proposed edge-cloud system can continue local environmental monitoring, persistence, decision-making, and actuator control during real network interruptions.

The cloud communication layer is therefore not required for immediate local safety responses, while asynchronous queueing supports eventual cloud synchronization after connectivity is restored.