import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = (
        Path.home()
        / "azure-iot-environment"
)


class ThingsBoardService:
    def __init__(self) -> None:
        load_dotenv(
            PROJECT_ROOT / ".env"
        )

        self.host = os.getenv(
            "THINGSBOARD_HOST",
            "",
        ).rstrip("/")

        self.token = os.getenv(
            "THINGSBOARD_DEVICE_TOKEN"
        )

        if not self.host:
            raise RuntimeError(
                "THINGSBOARD_HOST is missing."
            )

        if not self.token:
            raise RuntimeError(
                "THINGSBOARD_DEVICE_TOKEN "
                "is missing."
            )

    def send_telemetry(
            self,
            temperature: float,
            humidity: float,
            state: str,
    ) -> None:
        url = (
            f"{self.host}/api/v1/"
            f"{self.token}/telemetry"
        )

        payload = {
            "Actual_Temperature_C": temperature,
            "Actual_Humidity_Percent": humidity,
            "state": state,
        }

        response = requests.post(
            url,
            json=payload,
            timeout=10,
        )

        response.raise_for_status()