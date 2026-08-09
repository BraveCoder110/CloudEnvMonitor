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
            payload: dict,
    ) -> bool:
        url = (
            f"{self.host}/api/v1/"
            f"{self.token}/telemetry"
        )

        # ThingsBoard正式字段规范
        tb_payload = {
            "Actual_Temperature_C":
                payload["temperature"],

            "Actual_Humidity_Percent":
                payload["humidity"],

            "System_State":
                payload["state"],

            "Record_ID":
                payload["recordId"],
        }

        # 阈值以后如果payload里存在，也一起发送
        if "threshold" in payload:
            tb_payload[
                "High_Temperature_Threshold_C"
            ] = payload["threshold"]

        try:
            response = requests.post(
                url,
                json=tb_payload,
                timeout=5,
            )

            response.raise_for_status()

            return True

        except requests.RequestException as error:
            print(
                "ThingsBoard upload failed: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            return False