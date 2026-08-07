import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import adafruit_dht
import board
from azure.iot.device import IoTHubDeviceClient, Message
from dotenv import load_dotenv
from gpiozero import Buzzer, LED


# --------------------------------------------------
# GPIO configuration
# --------------------------------------------------

DHT_PIN = board.D4
LED_GPIO = 17
BUZZER_GPIO = 18


# --------------------------------------------------
# Application configuration
# --------------------------------------------------

DEVICE_ID = "stanfort-cloud-device"

HIGH_TEMPERATURE_C = 28.0
READ_INTERVAL_SECONDS = 10
MAX_SENSOR_RETRIES = 5
SENSOR_RETRY_DELAY_SECONDS = 2
ALARM_BEEP_SECONDS = 0.20

MAX_PENDING_UPLOADS_PER_ROUND = 10
SIMULATE_AZURE_OFFLINE = False

DATABASE_PATH = (
    Path.home()
    / "azure-iot-environment"
    / "database"
    / "environment.db"
)


class SystemState(Enum):
    NORMAL = "NORMAL"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    SENSOR_ERROR = "SENSOR_ERROR"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_dht11(
    sensor: adafruit_dht.DHT11,
) -> tuple[float, float] | None:
    for attempt in range(1, MAX_SENSOR_RETRIES + 1):
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
                f"  Sensor attempt {attempt}/"
                f"{MAX_SENSOR_RETRIES} failed: {error}"
            )

            if attempt < MAX_SENSOR_RETRIES:
                time.sleep(SENSOR_RETRY_DELAY_SECONDS)

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


def get_database_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def save_telemetry(
    payload: dict[str, Any],
) -> int:
    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO telemetry (
                device_id,
                temperature,
                humidity,
                state,
                led,
                buzzer,
                timestamp,
                upload_status,
                upload_attempts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0)
            """,
            (
                payload["deviceId"],
                payload["temperature"],
                payload["humidity"],
                payload["state"],
                int(payload["led"]),
                int(payload["buzzer"]),
                payload["timestamp"],
            ),
        )

        return int(cursor.lastrowid)


def get_pending_rows(
    limit: int,
) -> list[sqlite3.Row]:
    with get_database_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM telemetry
            WHERE upload_status = 'pending'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return rows


def row_to_payload(
    row: sqlite3.Row,
) -> dict[str, Any]:
    return {
        "recordId": row["id"],
        "deviceId": row["device_id"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "state": row["state"],
        "led": bool(row["led"]),
        "buzzer": bool(row["buzzer"]),
        "timestamp": row["timestamp"],
    }


def create_message(
    payload: dict[str, Any],
) -> Message:
    message = Message(
        json.dumps(
            payload,
            ensure_ascii=False,
        )
    )

    message.content_encoding = "utf-8"
    message.content_type = "application/json"

    message.custom_properties["systemState"] = payload["state"]
    message.custom_properties["recordId"] = str(
        payload["recordId"]
    )

    return message


def mark_uploaded(
    record_id: int,
) -> None:
    with get_database_connection() as connection:
        connection.execute(
            """
            UPDATE telemetry
            SET
                upload_status = 'uploaded',
                uploaded_at = ?,
                upload_attempts = upload_attempts + 1
            WHERE id = ?
            """,
            (
                utc_timestamp(),
                record_id,
            ),
        )


def mark_upload_failed(
    record_id: int,
) -> None:
    with get_database_connection() as connection:
        connection.execute(
            """
            UPDATE telemetry
            SET upload_attempts = upload_attempts + 1
            WHERE id = ?
            """,
            (record_id,),
        )


def upload_pending_rows(
    client: IoTHubDeviceClient,
) -> tuple[int, int]:
    pending_rows = get_pending_rows(
        MAX_PENDING_UPLOADS_PER_ROUND
    )

    if not pending_rows:
        print("Pending upload queue: empty")
        return 0, 0

    print(
        f"Pending upload queue: "
        f"{len(pending_rows)} record(s)"
    )

    uploaded_count = 0
    failed_count = 0

    for row in pending_rows:
        payload = row_to_payload(row)
        record_id = int(row["id"])

        try:
            message = create_message(payload)
            client.send_message(message)

            mark_uploaded(record_id)
            uploaded_count += 1

            print(
                f"  Record {record_id}: "
                "UPLOAD SUCCESS"
            )

        except Exception as error:
            mark_upload_failed(record_id)
            failed_count += 1

            print(
                f"  Record {record_id}: UPLOAD FAILED | "
                f"{type(error).__name__}: {error}"
            )

            # Network failure usually affects later messages too.
            break

    return uploaded_count, failed_count


def count_by_status() -> tuple[int, int]:
    with get_database_connection() as connection:
        pending = connection.execute(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE upload_status = 'pending'
            """
        ).fetchone()[0]

        uploaded = connection.execute(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE upload_status = 'uploaded'
            """
        ).fetchone()[0]

    return int(pending), int(uploaded)


def main() -> None:
    load_dotenv(
        Path.home()
        / "azure-iot-environment"
        / ".env"
    )

    connection_string = os.getenv(
        "IOTHUB_DEVICE_CONNECTION_STRING"
    )

    if not connection_string:
        raise RuntimeError(
            "IOTHUB_DEVICE_CONNECTION_STRING is missing."
        )

    if not DATABASE_PATH.exists():
        raise RuntimeError(
            f"Database not found: {DATABASE_PATH}"
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

    azure_connected = False

    print("=" * 72)
    print("Azure IoT Environmental Telemetry V2")
    print("Local SQLite cache enabled")
    print(f"Device ID             : {DEVICE_ID}")
    print(f"Database              : {DATABASE_PATH}")
    print(
        f"Temperature threshold : "
        f"{HIGH_TEMPERATURE_C:.1f} °C"
    )
    print(
        f"Upload interval       : "
        f"{READ_INTERVAL_SECONDS} seconds"
    )
    print("Press Ctrl+C to stop")
    print("=" * 72)

    try:
        try:
            if SIMULATE_AZURE_OFFLINE:
                print("SIMULATION: Azure is offline.")
                print("Local data collection and caching will continue.")
                azure_connected = False
            else:
                try:
                    print("Connecting to Azure IoT Hub...")
                    client.connect()
                    azure_connected = True
                    print("Azure connection established.")

                except Exception as error:
                    print(
                        "Initial Azure connection failed. "
                        "Local caching will continue."
                    )
                    print(f"{type(error).__name__}: {error}")

        except Exception as error:
            print(
                "Initial Azure connection failed. "
                "Local caching will continue."
            )
            print(
                f"{type(error).__name__}: {error}"
            )

        while True:
            print(
                "\n"
                + datetime.now().strftime(
                    "[%Y-%m-%d %H:%M:%S]"
                )
                + " Reading environment..."
            )

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
                "timestamp": utc_timestamp(),
            }

            record_id = save_telemetry(payload)

            print("Local database save: SUCCESS")
            print(f"Record ID   : {record_id}")
            print(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            if not azure_connected and not SIMULATE_AZURE_OFFLINE:
                try:
                    print(
                        "Attempting Azure reconnection..."
                    )
                    client.connect()
                    azure_connected = True
                    print(
                        "Azure reconnection successful."
                    )

                except Exception as error:
                    print(
                        "Azure still unavailable. "
                        "Record remains pending."
                    )
                    print(
                        f"{type(error).__name__}: {error}"
                    )

            if azure_connected:
                uploaded, failed = upload_pending_rows(
                    client
                )

                if failed > 0:
                    azure_connected = False

                print(
                    f"Upload round result: "
                    f"uploaded={uploaded}, failed={failed}"
                )

            pending_count, uploaded_count = count_by_status()

            print(
                f"Database status: pending={pending_count}, "
                f"uploaded={uploaded_count}"
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
