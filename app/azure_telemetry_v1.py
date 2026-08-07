import json
import os
import time
from datetime import datetime, timezone
from enum import Enum

import adafruit_dht
import board
from azure.iot.device import IoTHubDeviceClient, Message
from dotenv import load_dotenv
from gpiozero import Buzzer, LED


# --------------------------------------------------
# GPIO configuration
# --------------------------------------------------

DHT_PIN = board.D4       # Physical Pin 7
LED_GPIO = 17            # Physical Pin 11
BUZZER_GPIO = 18         # Physical Pin 12


# --------------------------------------------------
# Application configuration
# --------------------------------------------------

DEVICE_ID = "stanfort-cloud-device"

HIGH_TEMPERATURE_C = 28.0
READ_INTERVAL_SECONDS = 10
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 2
ALARM_BEEP_SECONDS = 0.20


class SystemState(Enum):
    NORMAL = "NORMAL"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    SENSOR_ERROR = "SENSOR_ERROR"


def read_dht11(
    sensor: adafruit_dht.DHT11,
) -> tuple[float, float] | None:
    """Read DHT11 data with retries."""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            temperature = sensor.temperature
            humidity = sensor.humidity

            if temperature is None or humidity is None:
                raise RuntimeError("Sensor returned empty data")

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
                f"  Attempt {attempt}/{MAX_RETRIES} failed: "
                f"{error}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    return None


def determine_state(
    temperature: float | None,
) -> SystemState:
    if temperature is None:
        return SystemState.SENSOR_ERROR

    if temperature >= HIGH_TEMPERATURE_C:
        return SystemState.HIGH_TEMPERATURE

    return SystemState.NORMAL


def apply_outputs(
    state: SystemState,
    led: LED,
    buzzer: Buzzer,
) -> tuple[bool, bool]:
    """
    Apply physical outputs.

    Returns:
        (led_on, buzzer_activated)
    """

    if state == SystemState.NORMAL:
        led.on()
        buzzer.off()
        return True, False

    if state == SystemState.HIGH_TEMPERATURE:
        led.on()

        buzzer.on()
        time.sleep(ALARM_BEEP_SECONDS)
        buzzer.off()

        return True, True

    led.off()
    buzzer.off()
    return False, False


def create_message(payload: dict) -> Message:
    message = Message(json.dumps(payload))

    message.content_encoding = "utf-8"
    message.content_type = "application/json"

    message.custom_properties["systemState"] = payload["state"]

    return message


def main() -> None:
    load_dotenv(
        os.path.expanduser(
            "~/azure-iot-environment/.env"
        )
    )

    connection_string = os.getenv(
        "IOTHUB_DEVICE_CONNECTION_STRING"
    )

    if not connection_string:
        raise RuntimeError(
            "IOTHUB_DEVICE_CONNECTION_STRING is missing."
        )

    sensor = adafruit_dht.DHT11(
        DHT_PIN,
        use_pulseio=False,
    )

    led = LED(LED_GPIO)
    buzzer = Buzzer(BUZZER_GPIO)

    client = IoTHubDeviceClient.create_from_connection_string(
        connection_string
    )

    sent_messages = 0
    failed_messages = 0

    print("=" * 70)
    print("Azure IoT Environmental Telemetry V1")
    print(f"Device ID              : {DEVICE_ID}")
    print(f"Temperature threshold  : {HIGH_TEMPERATURE_C:.1f} °C")
    print(f"Upload interval        : {READ_INTERVAL_SECONDS} seconds")
    print("Press Ctrl+C to stop")
    print("=" * 70)

    try:
        print("Connecting to Azure IoT Hub...")
        client.connect()
        print("Azure connection established.")

        while True:
            reading = read_dht11(sensor)

            if reading is None:
                temperature = None
                humidity = None
            else:
                temperature, humidity = reading

            state = determine_state(temperature)

            led_on, buzzer_activated = apply_outputs(
                state,
                led,
                buzzer,
            )

            payload = {
                "deviceId": DEVICE_ID,
                "temperature": temperature,
                "humidity": humidity,
                "state": state.value,
                "led": led_on,
                "buzzer": buzzer_activated,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            print("\nTelemetry payload:")
            print(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            try:
                message = create_message(payload)
                client.send_message(message)

                sent_messages += 1

                print(
                    f"Azure upload: SUCCESS | "
                    f"Sent: {sent_messages} | "
                    f"Failed: {failed_messages}"
                )

            except Exception as error:
                failed_messages += 1

                print(
                    f"Azure upload: FAILED | "
                    f"{type(error).__name__}: {error}"
                )

            time.sleep(READ_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")

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

        print("Azure client disconnected.")
        print("GPIO and DHT11 resources released safely.")


if __name__ == "__main__":
    main()
