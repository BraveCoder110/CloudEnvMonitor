# CloudEnvMonitor

```
CloudEnvMonitor/
├── .env
├── .venv/
│
├── app/
│   ├── edge_alert_v1.py    # 第一版本地边缘预警程序。
│   ├── azure_telemetry_v1.py   # 第一版Azure真实遥测上传程序。
│   └── azure_telemetry_v2_sqlite.py    # 目前最重要的主程序原型。
│
├── cloud/

│   └── thingsboard_test.py # ThingsBoard最小上传测试。
│
├── database/
│   ├── environment.db  # 实际SQLite数据库文件。
│   └── init_database.py    # 初始化SQLite数据库。
│
├── test_sensors/
│   ├── azure_connect_test.py   # Azure最小连接测试。
│   ├── dht11_led_test.py   # DHT11与LED联合测试。
│   ├── dht11_test.py   # 稳定版DHT11测试程序。
│   ├── test_active_buzzer.py   # 单独验证GPIO18和有源蜂鸣器。
│   └── test_pir.py # PIR状态变化测试
│
└── README.md
```