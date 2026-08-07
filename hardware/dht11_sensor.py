import time

import adafruit_dht
import board


class DHT11Sensor:
    def __init__(
            self,
            max_retries: int = 5,
            retry_delay: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.sensor = adafruit_dht.DHT11(
            board.D4,
            use_pulseio=False,
        )

    def read(
            self,
    ) -> tuple[float, float] | None:
        for attempt in range(
                1,
                self.max_retries + 1,
        ):
            try:
                temperature = self.sensor.temperature
                humidity = self.sensor.humidity

                if (
                        temperature is None
                        or humidity is None
                ):
                    raise RuntimeError(
                        "Sensor returned empty data"
                    )

                temperature = float(temperature)
                humidity = float(humidity)

                if not -20 <= temperature <= 60:
                    raise RuntimeError(
                        f"Invalid temperature: "
                        f"{temperature}"
                    )

                if not 0 <= humidity <= 100:
                    raise RuntimeError(
                        f"Invalid humidity: "
                        f"{humidity}"
                    )

                return temperature, humidity

            except RuntimeError as error:
                print(
                    f"  DHT11 attempt "
                    f"{attempt}/{self.max_retries} "
                    f"failed: {error}"
                )

                if attempt < self.max_retries:
                    time.sleep(
                        self.retry_delay
                    )

        return None

    def close(self) -> None:
        self.sensor.exit()