import time
from datetime import datetime

import adafruit_dht
import board
from gpiozero import LED


# DHT11 DATA -> GPIO4 / physical Pin 7
DHT_PIN = board.D4

# LED -> GPIO17 / physical Pin 11
LED_GPIO = 17

READ_INTERVAL_SECONDS = 4
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 2


def read_sensor(sensor: adafruit_dht.DHT11) -> tuple[float, float] | None:
    """Read DHT11 with retries."""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            temperature = sensor.temperature
            humidity = sensor.humidity

            if temperature is None or humidity is None:
                raise RuntimeError("Sensor returned empty data")

            if not -20 <= temperature <= 60:
                raise RuntimeError(
                    f"Invalid temperature value: {temperature}"
                )

            if not 0 <= humidity <= 100:
                raise RuntimeError(
                    f"Invalid humidity value: {humidity}"
                )

            return float(temperature), float(humidity)

        except RuntimeError as error:
            print(
                f"  Attempt {attempt}/{MAX_RETRIES} failed: "
                f"{error}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    return None


def update_led(led: LED, sensor_ok: bool) -> None:
    """
    LED meaning:
    ON  = valid DHT11 reading received
    OFF = current reading round failed
    """

    if sensor_ok:
        led.on()
    else:
        led.off()


def main() -> None:
    sensor = adafruit_dht.DHT11(
        DHT_PIN,
        use_pulseio=False,
    )

    led = LED(LED_GPIO)

    successful_readings = 0
    failed_rounds = 0

    print("=" * 62)
    print("DHT11 + LED Combined Test")
    print("DHT11: GPIO4 / physical Pin 7")
    print("LED  : GPIO17 / physical Pin 11")
    print("LED ON  = valid sensor reading")
    print("LED OFF = current reading round failed")
    print("Press Ctrl+C to stop")
    print("=" * 62)

    try:
        while True:
            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            print(f"\n[{timestamp}] Reading sensor...")

            result = read_sensor(sensor)

            if result is None:
                failed_rounds += 1
                update_led(led, sensor_ok=False)

                print("RESULT: FAILED")
                print("LED: OFF")
                print(
                    f"Successful readings: {successful_readings} | "
                    f"Failed rounds: {failed_rounds}"
                )

            else:
                temperature, humidity = result
                successful_readings += 1
                update_led(led, sensor_ok=True)

                print("RESULT: SUCCESS")
                print(f"Temperature : {temperature:.1f} °C")
                print(f"Humidity    : {humidity:.1f} %")
                print("LED         : ON")
                print(
                    f"Successful readings: {successful_readings} | "
                    f"Failed rounds: {failed_rounds}"
                )

            time.sleep(READ_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\nTest stopped by user.")

    finally:
        led.off()
        led.close()
        sensor.exit()

        print("LED switched off.")
        print("DHT11 resource released safely.")


if __name__ == "__main__":
    main()
