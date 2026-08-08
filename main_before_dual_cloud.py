import time

from cloud.azure_service import AzureService
from cloud.thingsboard_service import ThingsBoardService
from hardware.buzzer_controller import BuzzerController
from hardware.dht11_sensor import DHT11Sensor
from hardware.fan_controller import FanController
from hardware.led_controller import LEDController
from services.config_manager import ConfigManager
from services.edge_controller import EdgeController, SystemState


READ_INTERVAL_SECONDS = 5
DEFAULT_FAN_SPEED_LEVEL = 2


config = ConfigManager()
previous_state = None


def desired_properties_handler(
        patch: dict,
) -> None:
    print("\n" + "=" * 65)
    print("CLOUD CONFIGURATION UPDATE RECEIVED")
    print("=" * 65)

    old_config = config.get_all()

    accepted = config.update(patch)

    if not accepted:
        print("No supported configuration changes.")
        print("=" * 65)
        return

    effective_changes = {}

    for key, value in accepted.items():
        old_value = old_config.get(key)

        if old_value != value:
            effective_changes[key] = value

            print(
                f"{key}: "
                f"{old_value} -> {value}"
            )

    if not effective_changes:
        print(
            "Configuration received, "
            "but no effective values changed."
        )

    print("=" * 65)


def print_state_change(
        old_state,
        new_state,
) -> None:
    if old_state is None:
        return

    if old_state == new_state:
        return

    print("\n" + "=" * 65)

    if (
            old_state == SystemState.HIGH_TEMPERATURE
            and new_state == SystemState.NORMAL
    ):
        print("STATE RECOVERED")
    else:
        print("STATE CHANGED")

    print(
        f"{old_state.value} "
        f"-> {new_state.value}"
    )

    print("=" * 65)


def handle_state_outputs(
        state: SystemState,
        old_state,
        led: LEDController,
        buzzer: BuzzerController,
        fan: FanController,
) -> None:

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

    # Manual/disabled automatic control
    if not auto_mode:
        led.off()
        buzzer.off()

        if fan.power_on:
            fan.turn_off()

        return

    # NORMAL
    if state == SystemState.NORMAL:
        led.normal()
        buzzer.off()

        if fan.power_on:
            print(
                "Environment recovered. "
                "Turning fan OFF..."
            )

            fan.turn_off()

        return

    # HIGH TEMPERATURE
    if state == SystemState.HIGH_TEMPERATURE:
        led.alarm()

        # Buzzer only when ENTERING alarm state
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
                duration=0.5,
            )

        if fan_enabled:
            if not fan.power_on:
                print(
                    "High temperature detected. "
                    "Turning fan ON..."
                )

                fan.turn_on()

            if (
                    fan.power_on
                    and fan.speed_level
                    != DEFAULT_FAN_SPEED_LEVEL
            ):
                fan.set_speed(
                    DEFAULT_FAN_SPEED_LEVEL
                )

        else:
            if fan.power_on:
                print(
                    "Fan control disabled. "
                    "Turning fan OFF..."
                )

                fan.turn_off()

        return

    # SENSOR ERROR
    led.off()
    buzzer.off()

    if fan.power_on:
        print(
            "Sensor error. "
            "Turning fan OFF for safety..."
        )

        fan.turn_off()


def main() -> None:
    global previous_state

    sensor = DHT11Sensor()
    led = LEDController()
    buzzer = BuzzerController()
    fan = FanController()

    azure = AzureService(
        desired_properties_handler
    )

    thingsboard = ThingsBoardService()

    print("=" * 72)
    print(
        "Azure Edge-Cloud Environmental "
        "Control System"
    )
    print("Production Architecture V2")
    print("=" * 72)

    try:
        print(
            "Connecting to Azure IoT Hub..."
        )

        azure.connect()

        print(
            "Azure connection: ONLINE"
        )

        desired = (
            azure.get_desired_properties()
        )

        config.update(
            desired
        )

        print(
            "\nActive configuration:"
        )

        print(
            config.get_all()
        )

        print(
            "\nIMPORTANT:"
        )

        print(
            "Fan software state assumes "
            "the physical fan is OFF "
            "when the program starts."
        )

        print(
            "\nSystem running."
        )

        print(
            "Press Ctrl+C to stop."
        )

        print("=" * 72)

        while True:
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
                temperature, humidity = reading

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

            handle_state_outputs(
                state=state,
                old_state=old_state,
                led=led,
                buzzer=buzzer,
                fan=fan,
            )

            previous_state = state

            print(
                "\n----------------------------------------"
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
                f"{'ON' if state == SystemState.HIGH_TEMPERATURE else 'OFF'}"
            )

            print(
                f"Auto Mode   : "
                f"{config.get('autoMode')}"
            )

            print(
                f"Buzzer      : "
                f"{config.get('buzzerEnabled')}"
            )

            fan_status = fan.status()

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

            if temperature is not None:
                thingsboard_ok = (
                    thingsboard.send_telemetry(
                        temperature=temperature,
                        humidity=humidity,
                        state=state.value,
                        threshold=threshold,
                    )
                )

                print(
                    f"ThingsBoard : "
                    f"{'UPLOAD SUCCESS' if thingsboard_ok else 'UPLOAD FAILED'}"
                )

            else:
                print(
                    "ThingsBoard : SKIPPED "
                    "(sensor unavailable)"
                )

            time.sleep(
                READ_INTERVAL_SECONDS
            )

    except KeyboardInterrupt:
        print(
            "\nProgram stopped by user."
        )

    finally:
        buzzer.off()
        led.off()

        if fan.power_on:
            print(
                "Shutting down fan..."
            )

            fan.turn_off()

        azure.disconnect()

        buzzer.close()
        led.close()
        sensor.close()

        print(
            "System resources released safely."
        )


if __name__ == "__main__":
    main()