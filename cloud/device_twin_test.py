import os
import time
from pathlib import Path

from azure.iot.device import IoTHubDeviceClient
from dotenv import load_dotenv

from services.config_manager import ConfigManager


PROJECT_ROOT = (
        Path.home()
        / "azure-iot-environment"
)

ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

connection_string = os.getenv(
    "IOTHUB_DEVICE_CONNECTION_STRING"
)

if not connection_string:
    raise RuntimeError(
        "IOTHUB_DEVICE_CONNECTION_STRING is missing."
    )


config = ConfigManager()


def desired_properties_handler(
        patch: dict,
) -> None:
    print("\n" + "=" * 60)
    print("Azure Device Twin update received")
    print("Raw desired properties:")
    print(patch)

    old_threshold = config.get(
        "highTemperatureThreshold"
    )

    accepted = config.update(patch)

    if not accepted:
        print("No supported configuration changes found.")
        print("=" * 60)
        return

    print("Accepted configuration changes:")
    print(accepted)

    if "highTemperatureThreshold" in accepted:
        new_threshold = accepted[
            "highTemperatureThreshold"
        ]

        print(
            "Temperature threshold updated:"
        )
        print(
            f"{old_threshold:.1f} °C "
            f"-> {new_threshold:.1f} °C"
        )

    print("Current local configuration:")
    print(config.get_all())
    print("=" * 60)


def main() -> None:
    client = (
        IoTHubDeviceClient
        .create_from_connection_string(
            connection_string
        )
    )

    client.on_twin_desired_properties_patch_received = (
        desired_properties_handler
    )

    print("=" * 65)
    print("Azure Device Twin Configuration Test")
    print("=" * 65)

    try:
        print("Connecting to Azure IoT Hub...")
        client.connect()

        print("Connected successfully.")

        twin = client.get_twin()

        desired = twin.get(
            "desired",
            {},
        )

        print("\nCurrent Azure desired properties:")
        print(desired)

        accepted = config.update(desired)

        if accepted:
            print(
                "Initial desired properties applied:"
            )
            print(accepted)

        print("\nCurrent local configuration:")
        print(config.get_all())

        print("\nWaiting for cloud configuration changes...")
        print("Press Ctrl+C to stop.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")

    finally:
        try:
            client.disconnect()
        except Exception:
            pass

        print("Azure client disconnected.")


if __name__ == "__main__":
    main()