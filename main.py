"""
main.py

Azure + ThingsBoard Edge-Cloud Environmental Control System
Production V5

核心设计原则：
1. DHT11传感器采集、LED、蜂鸣器、风扇控制全部运行在主线程。
2. 每一条遥测数据必须先保存到SQLite。
3. Azure和ThingsBoard上传由后台线程负责。
4. 云端网络故障绝不能阻塞本地边缘控制。
5. Azure和ThingsBoard分别维护独立pending队列。
6. 网络恢复后，由后台同步线程自动补传历史记录。

重要：
启动程序前，请确认实体风扇处于关闭状态。
因为当前红外控制是开环控制，树莓派无法读取风扇真实状态。
"""

import time
from datetime import datetime, timezone

from cloud.azure_service import AzureService
from cloud.thingsboard_service import ThingsBoardService
from database.sqlite_service import SQLiteService
from hardware.buzzer_controller import BuzzerController
from hardware.dht11_sensor import DHT11Sensor
from hardware.fan_controller import FanController
from hardware.led_controller import LEDController
from services.background_cloud_sync import BackgroundCloudSync
from services.cloud_sync_service import CloudSyncService
from services.config_manager import ConfigManager
from services.edge_controller import EdgeController, SystemState


# ============================================================
# 基本配置
# ============================================================

DEVICE_ID = "stanfort-cloud-device"

# 主线程采集周期
READ_INTERVAL_SECONDS = 5

# 高温状态下，风扇自动设置为2档
DEFAULT_FAN_SPEED_LEVEL = 2


# ============================================================
# 全局配置管理
# ============================================================

config = ConfigManager()

# 用于判断状态是否发生变化
previous_state = None


# ============================================================
# 工具函数
# ============================================================

def utc_timestamp() -> str:
    """生成UTC ISO 8601时间戳。"""

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# Azure Device Twin回调
# ============================================================

def desired_properties_handler(
        patch: dict,
) -> None:
    """
    Azure Device Twin Desired Properties发生变化时执行。

    例如Azure将：
        highTemperatureThreshold: 30 -> 27

    ConfigManager会立即更新本地settings.json，
    下一轮边缘判断马上使用新阈值。
    """

    print("\n" + "=" * 68)
    print("CLOUD CONFIGURATION UPDATE RECEIVED")
    print("=" * 68)

    old_config = config.get_all()

    accepted = config.update(
        patch
    )

    if not accepted:
        print(
            "No supported configuration changes."
        )
        print("=" * 68)
        return

    effective_change_found = False

    for key, new_value in accepted.items():
        old_value = old_config.get(
            key
        )

        if old_value != new_value:
            effective_change_found = True

            print(
                f"{key}: "
                f"{old_value} -> {new_value}"
            )

    if not effective_change_found:
        print(
            "Configuration received, "
            "but no effective values changed."
        )

    print("=" * 68)


# ============================================================
# 状态变化日志
# ============================================================

def print_state_change(
        old_state,
        new_state,
) -> None:
    """
    只有系统状态真正改变时打印醒目的状态日志。
    """

    if old_state is None:
        return

    if old_state == new_state:
        return

    print("\n" + "=" * 68)

    if (
            old_state
            == SystemState.HIGH_TEMPERATURE
            and new_state
            == SystemState.NORMAL
    ):
        print("STATE RECOVERED")

    else:
        print("STATE CHANGED")

    print(
        f"{old_state.value} "
        f"-> {new_state.value}"
    )

    print("=" * 68)


# ============================================================
# 边缘执行器控制
# ============================================================

def apply_outputs(
        state: SystemState,
        old_state,
        led: LEDController,
        buzzer: BuzzerController,
        fan: FanController,
) -> tuple[bool, bool]:
    """
    根据当前环境状态控制本地硬件。

    返回：
        led_on
        buzzer_triggered

    注意：
    buzzer_triggered表示“这一轮是否真的鸣叫”，
    而不是蜂鸣器功能是否启用。
    """

    auto_mode = bool(
        config.get(
            "autoMode",
            True,
        )
    )

    buzzer_enabled = bool(
        config.get(
            "buzzerEnabled",
            True,
        )
    )

    fan_enabled = bool(
        config.get(
            "fanEnabled",
            True,
        )
    )

    # --------------------------------------------------------
    # 自动模式关闭
    # --------------------------------------------------------

    if not auto_mode:
        led.off()
        buzzer.off()

        if fan.power_on:
            print(
                "Auto mode disabled. "
                "Turning fan OFF..."
            )

            fan.turn_off()

        return False, False

    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    if state == SystemState.NORMAL:
        # 正常状态：普通LED关闭
        led.normal()

        buzzer.off()

        # 如果之前因为高温启动了风扇，则恢复后关闭
        if fan.power_on:
            print(
                "Environment recovered. "
                "Turning fan OFF..."
            )

            fan.turn_off()

        return False, False

    # --------------------------------------------------------
    # HIGH TEMPERATURE
    # --------------------------------------------------------

    if state == SystemState.HIGH_TEMPERATURE:
        # 高温：LED持续亮
        led.alarm()

        buzzer_triggered = False

        # 蜂鸣器只在“刚刚进入高温状态”的时候响一次
        if (
                old_state
                != SystemState.HIGH_TEMPERATURE
                and buzzer_enabled
        ):
            print(
                "High temperature detected. "
                "Triggering buzzer once..."
            )

            buzzer.alarm(
                duration=0.5
            )

            buzzer_triggered = True

        # ----------------------------------------------------
        # 自动风扇控制
        # ----------------------------------------------------

        if fan_enabled:

            # 风扇当前关闭，则先开机
            if not fan.power_on:
                print(
                    "High temperature detected. "
                    "Turning fan ON..."
                )

                fan.turn_on()

            # 风扇开启后，自动调整到2档
            if (
                    fan.power_on
                    and fan.speed_level
                    != DEFAULT_FAN_SPEED_LEVEL
            ):
                fan.set_speed(
                    DEFAULT_FAN_SPEED_LEVEL
                )

        else:
            # Azure把fanEnabled关闭时，即使高温也关闭风扇
            if fan.power_on:
                print(
                    "Fan control disabled. "
                    "Turning fan OFF..."
                )

                fan.turn_off()

        return True, buzzer_triggered

    # --------------------------------------------------------
    # SENSOR ERROR
    # --------------------------------------------------------

    # 传感器异常时采取安全策略
    led.off()
    buzzer.off()

    if fan.power_on:
        print(
            "Sensor error detected. "
            "Turning fan OFF for safety..."
        )

        fan.turn_off()

    return False, False


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    global previous_state

    # ========================================================
    # 1. 初始化硬件
    # ========================================================

    sensor = DHT11Sensor()

    led = LEDController()

    buzzer = BuzzerController()

    fan = FanController()

    # ========================================================
    # 2. 初始化SQLite
    # ========================================================

    database = SQLiteService()

    # ========================================================
    # 3. 初始化Azure和ThingsBoard
    # ========================================================

    azure = AzureService(
        desired_properties_handler
    )

    thingsboard = ThingsBoardService()

    # ========================================================
    # 4. 创建双云同步服务
    # ========================================================

    cloud_sync = CloudSyncService(
        database=database,
        azure=azure,
        thingsboard=thingsboard,
    )

    # ========================================================
    # 5. 创建后台Cloud Worker
    #
    # 这是Production V5最重要的改变：
    #
    # Azure / ThingsBoard通信不再运行在主线程。
    #
    # 即使Azure网络调用阻塞，
    # DHT11、SQLite、LED、蜂鸣器、风扇仍继续工作。
    # ========================================================

    background_sync = BackgroundCloudSync(
        sync_service=cloud_sync,
        interval_seconds=5,
    )

    # ========================================================
    # 启动信息
    # ========================================================

    print("=" * 76)
    print(
        "Azure + ThingsBoard Edge-Cloud "
        "Environmental Control System"
    )

    print("Production Architecture V5")

    print(
        "Edge / Cloud communication decoupled"
    )

    print(
        "SQLite dual-cloud queue enabled"
    )

    print("=" * 76)

    try:

        # ====================================================
        # IMPORTANT:
        #
        # 不再在这里调用：
        #
        #     azure.connect()
        #
        # 原因：
        # Azure connect在真实断网时可能阻塞。
        #
        # Azure连接全部交给后台Cloud Worker。
        # 主线程必须始终能够启动并运行。
        # ====================================================

        print(
            "\nLocal edge system starting..."
        )

        print(
            "Cloud connection will be handled "
            "by background worker."
        )

        print(
            "\nActive local configuration:"
        )

        print(
            config.get_all()
        )

        print(
            "\nIMPORTANT:"
        )

        print(
            "Physical fan must be OFF "
            "before starting this program."
        )

        # ====================================================
        # 启动后台云同步线程
        # ====================================================

        background_sync.start()

        print(
            "\nBackground cloud synchronization "
            "started."
        )

        print(
            "Main edge-control loop started."
        )

        print(
            "Press Ctrl+C to stop."
        )

        print("=" * 76)

        # ====================================================
        # MAIN EDGE LOOP
        # ====================================================

        while True:

            cycle_start = datetime.now()

            print(
                "\n\n"
                + "#" * 76
            )

            print(
                cycle_start.strftime(
                    "[%Y-%m-%d %H:%M:%S] "
                    "EDGE CYCLE"
                )
            )

            print(
                "#" * 76
            )

            # =================================================
            # STEP A
            # 读取DHT11
            # =================================================

            reading = sensor.read()

            threshold = float(
                config.get(
                    "highTemperatureThreshold",
                    28.0,
                )
            )

            if reading is None:
                temperature = None
                humidity = None

            else:
                (
                    temperature,
                    humidity,
                ) = reading

            # =================================================
            # STEP B
            # 本地边缘状态判断
            # =================================================

            state = (
                EdgeController
                .determine_state(
                    temperature,
                    threshold,
                )
            )

            old_state = previous_state

            print_state_change(
                old_state,
                state,
            )

            # =================================================
            # STEP C
            # LED / Buzzer / Fan控制
            #
            # 注意：
            # 到这里完全不需要互联网。
            # =================================================

            (
                led_on,
                buzzer_triggered,
            ) = apply_outputs(
                state=state,
                old_state=old_state,
                led=led,
                buzzer=buzzer,
                fan=fan,
            )

            previous_state = state

            fan_status = fan.status()

            # =================================================
            # STEP D
            # 打印当前边缘状态
            # =================================================

            print(
                "\n--- Edge status ---"
            )

            if temperature is None:

                print(
                    "Temperature : unavailable"
                )

                print(
                    "Humidity    : unavailable"
                )

            else:

                print(
                    f"Temperature : "
                    f"{temperature:.1f} °C"
                )

                print(
                    f"Humidity    : "
                    f"{humidity:.1f} %"
                )

            print(
                f"Threshold   : "
                f"{threshold:.1f} °C"
            )

            print(
                f"State       : "
                f"{state.value}"
            )

            print(
                f"LED         : "
                f"{'ON' if led_on else 'OFF'}"
            )

            print(
                f"Buzzer Event: "
                f"{buzzer_triggered}"
            )

            print(
                f"Fan Power   : "
                f"{fan_status['powerOn']}"
            )

            print(
                f"Fan Speed   : "
                f"{fan_status['speedLevel']}"
            )

            print(
                f"Oscillation : "
                f"{fan_status['oscillationOn']}"
            )

            # =================================================
            # STEP E
            # 创建遥测数据
            # =================================================

            payload = {
                "deviceId": DEVICE_ID,
                "temperature": temperature,
                "humidity": humidity,
                "state": state.value,
                "led": led_on,
                "buzzer": buzzer_triggered,
                "timestamp": utc_timestamp(),
            }

            # =================================================
            # STEP F
            # SQLite FIRST
            #
            # 这是系统可靠性的核心：
            #
            # 无论Azure和ThingsBoard是否在线，
            # 每一条数据都先保存到本地SQLite。
            # =================================================

            record_id = (
                database.save_telemetry(
                    payload
                )
            )

            print(
                "\nSQLite save : SUCCESS "
                f"(Record {record_id})"
            )

            # =================================================
            # STEP G
            # 查询双云队列状态
            #
            # 注意：
            # 主线程这里只“读取状态”，
            # 绝不执行Azure/ThingsBoard网络请求。
            # =================================================

            queue_status = (
                database.count_status()
            )

            print(
                "\n--- Cloud queue status ---"
            )

            print(
                f"Total records       : "
                f"{queue_status['total']}"
            )

            print(
                f"Azure pending       : "
                f"{queue_status['azurePending']}"
            )

            print(
                f"ThingsBoard pending : "
                f"{queue_status['thingsboardPending']}"
            )

            # =================================================
            # STEP H
            # 等待下一轮
            # =================================================

            print(
                f"\nNext edge cycle in "
                f"{READ_INTERVAL_SECONDS} seconds..."
            )

            time.sleep(
                READ_INTERVAL_SECONDS
            )

    except KeyboardInterrupt:

        print(
            "\n\nProgram stopped by user."
        )

    finally:

        # ====================================================
        # 安全退出
        # ====================================================

        print(
            "\nStopping system..."
        )

        # 先通知后台线程停止
        background_sync.stop()

        # 关闭蜂鸣器和LED
        buzzer.off()
        led.off()

        # 如果风扇当前开启，关闭风扇
        if fan.power_on:

            print(
                "Shutting down fan..."
            )

            fan.turn_off()

        # 断开Azure
        azure.disconnect()

        # 释放GPIO / DHT资源
        buzzer.close()
        led.close()
        sensor.close()

        print(
            "System resources released safely."
        )

        print(
            "Production V5 stopped."
        )


if __name__ == "__main__":
    main()