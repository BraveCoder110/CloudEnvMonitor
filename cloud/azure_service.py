import json
import os
from pathlib import Path
from typing import Callable

from azure.iot.device import (
    IoTHubDeviceClient,
    Message,
)
from dotenv import load_dotenv


PROJECT_ROOT = (
        Path.home()
        / "azure-iot-environment"
)


class AzureService:
    def __init__(
            self,
            desired_properties_handler:
            Callable | None = None,
    ) -> None:

        load_dotenv(
            PROJECT_ROOT / ".env"
        )

        self.connection_string = os.getenv(
            "IOTHUB_DEVICE_CONNECTION_STRING"
        )

        if not self.connection_string:
            raise RuntimeError(
                "Azure IoT Hub connection string "
                "is missing."
            )

        self.desired_properties_handler = (
            desired_properties_handler
        )

        self.client = None
        self.connected = False

        self._create_client()

    def _create_client(self) -> None:
        self.client = (
            IoTHubDeviceClient
            .create_from_connection_string(
                self.connection_string
            )
        )

        if (
                self.desired_properties_handler
                is not None
        ):
            (
                self.client
                .on_twin_desired_properties_patch_received
            ) = self.desired_properties_handler

    def connect(self) -> bool:
        try:
            if self.client is None:
                self._create_client()

            self.client.connect()

            self.connected = True

            print(
                "Azure connection: ONLINE"
            )

            return True

        except Exception as error:
            self.connected = False

            print(
                "Azure connection: OFFLINE | "
                f"{type(error).__name__}: "
                f"{error}"
            )

            return False

    def reconnect(self) -> bool:
        print(
            "Attempting Azure reconnection..."
        )

        try:
            if self.client is not None:
                try:
                    self.client.disconnect()
                except Exception:
                    pass

            self.client = None

            self._create_client()

            return self.connect()

        except Exception as error:
            self.connected = False

            print(
                "Azure reconnection failed: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            return False

    def disconnect(self) -> None:
        try:
            if self.client is not None:
                self.client.disconnect()
        except Exception:
            pass

        self.connected = False

    def get_desired_properties(
            self,
    ) -> dict:
        if self.client is None:
            raise RuntimeError(
                "Azure client unavailable."
            )

        twin = self.client.get_twin()

        return twin.get(
            "desired",
            {},
        )

    def send_telemetry(
            self,
            payload: dict,
    ) -> bool:
        if (
                self.client is None
                or not self.connected
        ):
            return False

        try:
            message = Message(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                )
            )

            message.content_encoding = "utf-8"
            message.content_type = (
                "application/json"
            )

            if "state" in payload:
                message.custom_properties[
                    "systemState"
                ] = str(
                    payload["state"]
                )

            if "recordId" in payload:
                message.custom_properties[
                    "recordId"
                ] = str(
                    payload["recordId"]
                )

            self.client.send_message(
                message
            )

            return True

        except Exception as error:
            self.connected = False

            print(
                "Azure telemetry upload failed: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            return False