# CloudEnvMonitor

```
CloudEnvMonitor/
├── .env # 环境变量
├── .venv/
│
├── cloud/
│   ├── azure_service.py    # azure server
│   └── thingsboard_service.py   # things board server
│
├── config/
│   └── settings.json
│
├── database/
│   ├── environment.db  # 实际SQLite数据库文件。
│   └── init_database.py    # 初始化SQLite数据库。
│
├── experiments/    # 实验部分，详见experiments分支，未合并到main分支
│
├── hardware/
│   ├── buzzer_controller.py   # 蜂鸣器
│   ├── dht11_sensor.py   # dht11
│   ├── fan_controller.py   # 遥控风扇
│   └── led_controller.py   # led灯
│
├── old_structure/    # 老版本，忽略
│
├── services/
│   ├── background_cloud_sync.py   # 双云(azure/thingsboard)同步service
│   ├── cloud_sync_service.py   # 双云同步data组织
│   ├── config_manager.py    
│   └── edge_controller.py   
│
├── main.py
└── README.md
```
