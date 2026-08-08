import os
from pathlib import Path
from typing import Callable

from azure.iot.device import IoTHubDeviceClient
from dotenv import load_dotenv


PROJECT_ROOT = (
        Path.home()
        / "azure-iot-environment"
)


class AzureService:
    def __init__(
            self,
            desired_properties_handler: Callable,
    ) -> None:
        load_dotenv(
            PROJECT_ROOT / ".env"
        )

        connection_string = os.getenv(
            "IOTHUB_DEVICE_CONNECTION_STRING"
        )

        if not connection_string:
            raise RuntimeError(
                "Azure IoT Hub connection string "
                "is missing."
            )

        self.client = (
            IoTHubDeviceClient
            .create_from_connection_string(
                connection_string
            )
        )

        self.client.on_twin_desired_properties_patch_received = (
            desired_properties_handler
        )

    def connect(self) -> None:
        self.client.connect()

    def disconnect(self) -> None:
        try:
            self.client.disconnect()
        except Exception:
            pass

    def get_desired_properties(
            self,
    ) -> dict:
        twin = self.client.get_twin()

        return twin.get(
            "desired",
            {},
        )