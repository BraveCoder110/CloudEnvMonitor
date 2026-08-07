import time
from datetime import datetime
from enum import Enum

import adafruit_dht
import board
from gpiozero import Buzzer, LED


# -------------------------------------------------
# GPIO configuration
# -------------------------------------------------

DHT_PIN = board.D4       # GPIO4, physical Pin 7
LED_GPIO = 17            # GPIO17, physical Pin 11
BUZZER_GPIO = 18         # GPIO18, physical Pin 12


# -------------------------------------------------
# System configuration
# -------------------------------------------------

# 为了方便现场测试，先设置为26°C。
# 后面可以根据你的实际环境修改。
HIGH_TEMPERATURE_C = 26.0

READ_INTERVAL_SECONDS = 4
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 2

# 报警蜂鸣时间
ALARM_BEEP_SECONDS = 0.25

# 故障提示时间
ERROR_BEEP_SECONDS = 0.08


class SystemState(Enum):
    NORMAL = "NORMAL"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    SENSOR_ERROR = "SENSOR_ERROR"


def read_dht11(
    sensor: adafruit_dht.DHT11,
) -> tuple[float, float] | None:
    """
    Read temperature and humidity from DHT11.

    Returns:
        (temperature, humidity) when successful.
        None when all retries fail.
    """

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
    """Determine the local edge state."""

    if temperature is None:
        return SystemState.SENSOR_ERROR

    if temperature >= HIGH_TEMPERATURE_C:
        return SystemState.HIGH_TEMPERATURE

    return SystemState.NORMAL


def apply_normal_state(
    led: LED,
    buzzer: Buzzer,
) -> None:
    """Normal environment: LED on, buzzer off."""

    led.on()
    buzzer.off()


def apply_high_temperature_state(
    led: LED,
    buzzer: Buzzer,
) -> None:
    """High temperature: LED flashes and buzzer beeps."""

    led.on()
    buzzer.on()
    time.sleep(ALARM_BEEP_SECONDS)

    buzzer.off()
    led.off()
    time.sleep(ALARM_BEEP_SECONDS)

    led.on()


def apply_sensor_error_state(
    led: LED,
    buzzer: Buzzer,
) -> None:
    """Sensor error: LED off and two short error beeps."""

    led.off()

    for _ in range(2):
        buzzer.on()
        time.sleep(ERROR_BEEP_SECONDS)

        buzzer.off()
        time.sleep(0.15)


def main() -> None:
    sensor = adafruit_dht.DHT11(
        DHT_PIN,
        use_pulseio=False,
    )

    led = LED(LED_GPIO)
    buzzer = Buzzer(BUZZER_GPIO)

    successful_readings = 0
    failed_rounds = 0

    print("=" * 66)
    print("Azure IoT Environment System - Edge Alert V1")
    print(f"High-temperature threshold: {HIGH_TEMPERATURE_C:.1f} °C")
    print("NORMAL           : LED ON, buzzer OFF")
    print("HIGH TEMPERATURE : LED FLASH, buzzer BEEP")
    print("SENSOR ERROR     : LED OFF, two short beeps")
    print("Press Ctrl+C to stop")
    print("=" * 66)

    try:
        while True:
            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            print(f"\n[{timestamp}] Reading environment...")

            reading = read_dht11(sensor)

            if reading is None:
                failed_rounds += 1
                state = determine_state(None)

                apply_sensor_error_state(led, buzzer)

                print(f"State       : {state.value}")
                print("Temperature : unavailable")
                print("Humidity    : unavailable")

            else:
                temperature, humidity = reading
                successful_readings += 1

                state = determine_state(temperature)

                if state == SystemState.NORMAL:
                    apply_normal_state(led, buzzer)

                elif state == SystemState.HIGH_TEMPERATURE:
                    apply_high_temperature_state(
                        led,
                        buzzer,
                    )

                print(f"State       : {state.value}")
                print(f"Temperature : {temperature:.1f} °C")
                print(f"Humidity    : {humidity:.1f} %")

            print(
                f"Successful readings: {successful_readings} | "
                f"Failed rounds: {failed_rounds}"
            )

            time.sleep(READ_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\nProgram stopped by user.")

    finally:
        buzzer.off()
        led.off()

        buzzer.close()
        led.close()
        sensor.exit()

        print("LED switched off.")
        print("Buzzer switched off.")
        print("DHT11 resource released safely.")


if __name__ == "__main__":
    main()
