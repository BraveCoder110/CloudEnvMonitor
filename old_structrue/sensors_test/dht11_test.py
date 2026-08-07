import time
from datetime import datetime

import adafruit_dht
import board


# DHT11 DATA连接到GPIO4，也就是树莓派物理Pin 7
DHT_PIN = board.D4

# DHT11较慢，不建议读取得太频繁
READ_INTERVAL_SECONDS = 4

# 每一轮最多尝试几次
MAX_RETRIES = 5

# 每次重试之间等待多久
RETRY_DELAY_SECONDS = 2


def create_sensor() -> adafruit_dht.DHT11:
    """创建DHT11对象。"""
    return adafruit_dht.DHT11(
        DHT_PIN,
        use_pulseio=False,
    )


def read_sensor(
    sensor: adafruit_dht.DHT11,
) -> tuple[float, float] | None:
    """
    尝试多次读取DHT11。

    成功时返回：
        (temperature, humidity)

    全部失败时返回：
        None
    """

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            temperature = sensor.temperature
            humidity = sensor.humidity

            if temperature is None or humidity is None:
                raise RuntimeError("Sensor returned empty data")

            if not 0 <= humidity <= 100:
                raise RuntimeError(
                    f"Invalid humidity value: {humidity}"
                )

            if not -20 <= temperature <= 60:
                raise RuntimeError(
                    f"Invalid temperature value: {temperature}"
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


def main() -> None:
    sensor = create_sensor()
    successful_readings = 0
    failed_rounds = 0

    print("=" * 58)
    print("DHT11 Stable Test")
    print("DATA pin: GPIO4 / physical Pin 7")
    print("Power: 3.3V")
    print("Press Ctrl+C to stop")
    print("=" * 58)

    try:
        while True:
            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            print(f"\n[{timestamp}] Reading sensor...")

            result = read_sensor(sensor)

            if result is None:
                failed_rounds += 1

                print(
                    "RESULT: FAILED — no valid reading "
                    f"after {MAX_RETRIES} attempts"
                )
                print(
                    f"Successful readings: {successful_readings} | "
                    f"Failed rounds: {failed_rounds}"
                )
            else:
                temperature, humidity = result
                successful_readings += 1

                print("RESULT: SUCCESS")
                print(f"Temperature : {temperature:.1f} °C")
                print(f"Humidity    : {humidity:.1f} %")
                print(
                    f"Successful readings: {successful_readings} | "
                    f"Failed rounds: {failed_rounds}"
                )

            time.sleep(READ_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\nTest stopped by user.")

    finally:
        sensor.exit()
        print("DHT11 resource released safely.")


if __name__ == "__main__":
    main()
