import time

from cloud.azure_service import AzureService
from hardware.buzzer_controller import (
    BuzzerController,
)
from hardware.dht11_sensor import DHT11Sensor
from hardware.led_controller import LEDController
from services.config_manager import ConfigManager
from services.edge_controller import (
    EdgeController,
    SystemState,
)


READ_INTERVAL_SECONDS = 5


config = ConfigManager()

previous_state = None


def desired_properties_handler(
        patch: dict,
) -> None:
    print("\n" + "=" * 65)
    print("CLOUD CONFIGURATION UPDATE RECEIVED")
    print("=" * 65)

    old_config = config.get_all()

    accepted = config.update(
        patch
    )

    if not accepted:
        print(
            "No supported configuration changes."
        )
        return

    for key, value in accepted.items():
        print(
            f"{key}: "
            f"{old_config.get(key)} "
            f"-> {value}"
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

    print("=" * 65)


def main() -> None:
    global previous_state

    sensor = DHT11Sensor()
    led = LEDController()
    buzzer = BuzzerController()

    azure = AzureService(
        desired_properties_handler
    )

    print("=" * 70)
    print(
        "Azure Edge-Cloud Environmental "
        "Control System"
    )
    print("Production Architecture V1")
    print("=" * 70)

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
            "\nSystem running."
        )

        print(
            "Press Ctrl+C to stop."
        )

        print("=" * 70)

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

            print_state_change(
                previous_state,
                state,
            )

            previous_state = state

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

            if not auto_mode:
                led.off()
                buzzer.off()

            elif (
                    state
                    == SystemState.NORMAL
            ):
                led.normal()
                buzzer.off()

            elif (
                    state
                    == SystemState.HIGH_TEMPERATURE
            ):
                led.alarm()

                if buzzer_enabled:
                    buzzer.alarm()
                else:
                    buzzer.off()

            else:
                led.off()
                buzzer.off()

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
                f"{auto_mode}"
            )

            print(
                f"Buzzer      : "
                f"{buzzer_enabled}"
            )

            time.sleep(
                READ_INTERVAL_SECONDS
            )

    except KeyboardInterrupt:
        print(
            "\nProgram stopped by user."
        )

    finally:
        azure.disconnect()

        buzzer.close()
        led.close()
        sensor.close()

        print(
            "System resources "
            "released safely."
        )


if __name__ == "__main__":
    main()