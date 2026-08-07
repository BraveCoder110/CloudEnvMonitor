import os
import time
from pathlib import Path

import adafruit_dht
import board
from azure.iot.device import IoTHubDeviceClient
from dotenv import load_dotenv
from gpiozero import Buzzer, LED

from services.config_manager import ConfigManager


# =========================================================
# Project paths
# =========================================================

PROJECT_ROOT = Path.home() / "azure-iot-environment"
ENV_PATH = PROJECT_ROOT / ".env"


# =========================================================
# GPIO configuration
# =========================================================

DHT_PIN = board.D4       # Physical Pin 7
LED_GPIO = 17            # Physical Pin 11
BUZZER_GPIO = 18         # Physical Pin 12


# =========================================================
# Runtime configuration
# =========================================================

READ_INTERVAL_SECONDS = 5
MAX_SENSOR_RETRIES = 5
SENSOR_RETRY_DELAY_SECONDS = 2
ALARM_BEEP_SECONDS = 0.20


# =========================================================
# Configuration manager
# =========================================================

config = ConfigManager()


def read_dht11(sensor):
    """
    Read DHT11 with retries.
    """

    for attempt in range(1, MAX_SENSOR_RETRIES + 1):
        try:
            temperature = sensor.temperature
            humidity = sensor.humidity

            if temperature is None or humidity is None:
                raise RuntimeError(
                    "Sensor returned empty data"
                )

            temperature = float(temperature)
            humidity = float(humidity)

            if not -20 <= temperature <= 60:
                raise RuntimeError(
                    f"Invalid temperature: {temperature}"
                )

            if not 0 <= humidity <= 100:
                raise RuntimeError(
                    f"Invalid humidity: {humidity}"
                )

            return temperature, humidity

        except RuntimeError as error:
            print(
                f"  Sensor attempt "
                f"{attempt}/{MAX_SENSOR_RETRIES} failed: "
                f"{error}"
            )

            if attempt < MAX_SENSOR_RETRIES:
                time.sleep(
                    SENSOR_RETRY_DELAY_SECONDS
                )

    return None


def desired_properties_handler(patch):
    """
    Handle Azure Device Twin desired-property updates.
    """

    print("\n" + "=" * 65)
    print("CLOUD CONFIGURATION UPDATE RECEIVED")
    print("=" * 65)

    old_config = config.get_all()

    accepted = config.update(patch)

    if not accepted:
        print("No supported configuration changes.")
        return

    new_config = config.get_all()

    print("Accepted changes:")

    for key, value in accepted.items():
        print(
            f"  {key}: "
            f"{old_config.get(key)} -> {value}"
        )

    print("\nNew active configuration:")
    print(new_config)

    print("=" * 65)


def determine_state(temperature):
    """
    Determine system state using the CURRENT cloud/local threshold.
    """

    if temperature is None:
        return "SENSOR_ERROR"

    threshold = float(
        config.get(
            "highTemperatureThreshold",
            28.0,
        )
    )

    if temperature >= threshold:
        return "HIGH_TEMPERATURE"

    return "NORMAL"


def apply_outputs(
        state,
        led,
        buzzer,
):
    """
    Control local physical outputs.
    """

    buzzer_enabled = bool(
        config.get(
            "buzzerEnabled",
            True,
        )
    )

    auto_mode = bool(
        config.get(
            "autoMode",
            True,
        )
    )

    if not auto_mode:
        led.off()
        buzzer.off()

        return

    if state == "NORMAL":
        led.on()
        buzzer.off()

    elif state == "HIGH_TEMPERATURE":
        led.on()

        if buzzer_enabled:
            buzzer.on()
            time.sleep(ALARM_BEEP_SECONDS)
            buzzer.off()

    else:
        led.off()
        buzzer.off()


def main():
    load_dotenv(ENV_PATH)

    connection_string = os.getenv(
        "IOTHUB_DEVICE_CONNECTION_STRING"
    )

    if not connection_string:
        raise RuntimeError(
            "IOTHUB_DEVICE_CONNECTION_STRING "
            "is missing."
        )

    sensor = adafruit_dht.DHT11(
        DHT_PIN,
        use_pulseio=False,
    )

    led = LED(LED_GPIO)
    buzzer = Buzzer(BUZZER_GPIO)

    client = (
        IoTHubDeviceClient
        .create_from_connection_string(
            connection_string
        )
    )

    client.on_twin_desired_properties_patch_received = (
        desired_properties_handler
    )

    print("=" * 70)
    print("Azure Edge-Cloud Environmental Control System")
    print("MAIN APPLICATION")
    print("=" * 70)

    try:
        print("Connecting to Azure IoT Hub...")

        client.connect()

        print("Azure connection: ONLINE")

        # -------------------------------------------------
        # Retrieve current Azure Device Twin configuration
        # -------------------------------------------------

        twin = client.get_twin()

        desired = twin.get(
            "desired",
            {},
        )

        initial_updates = config.update(
            desired
        )

        if initial_updates:
            print(
                "Azure desired properties "
                "loaded at startup."
            )

        print("\nActive configuration:")
        print(config.get_all())

        print("\nSystem running.")
        print("Press Ctrl+C to stop.")
        print("=" * 70)

        while True:
            reading = read_dht11(sensor)

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

            state = determine_state(
                temperature
            )

            apply_outputs(
                state,
                led,
                buzzer,
            )

            print("\n----------------------------------------")

            if temperature is None:
                print("Temperature : unavailable")
                print("Humidity    : unavailable")
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
                f"{state}"
            )

            print(
                f"Auto Mode   : "
                f"{config.get('autoMode')}"
            )

            print(
                f"Buzzer      : "
                f"{config.get('buzzerEnabled')}"
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

        try:
            client.disconnect()
        except Exception:
            pass

        buzzer.close()
        led.close()
        sensor.exit()

        print(
            "System resources released safely."
        )


if __name__ == "__main__":
    main()