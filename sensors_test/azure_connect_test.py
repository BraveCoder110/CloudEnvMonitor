import json
import os

from azure.iot.device import IoTHubDeviceClient
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv(
    "IOTHUB_DEVICE_CONNECTION_STRING"
)

if not connection_string:
    raise RuntimeError(
        "Connection string not found in .env"
    )

print("Connecting to Azure IoT Hub...")

client = IoTHubDeviceClient.create_from_connection_string(
    connection_string
)

client.connect()

print("Connected successfully.")

message = json.dumps(
    {
        "device": "raspberrypi-edge-01",
        "status": "online"
    }
)

client.send_message(message)

print("Message sent successfully.")

client.disconnect()

print("Disconnected.")
