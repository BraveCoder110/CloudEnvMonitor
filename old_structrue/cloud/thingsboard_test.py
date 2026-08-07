import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


ENV_PATH = Path.home() / "azure-iot-environment" / ".env"

load_dotenv(ENV_PATH)

thingsboard_host = os.getenv("THINGSBOARD_HOST", "").rstrip("/")
access_token = os.getenv("THINGSBOARD_DEVICE_TOKEN")

if not thingsboard_host:
    print("ERROR: THINGSBOARD_HOST is missing from .env")
    sys.exit(1)

if not access_token:
    print("ERROR: THINGSBOARD_DEVICE_TOKEN is missing from .env")
    sys.exit(1)


telemetry_url = (
    f"{thingsboard_host}/api/v1/"
    f"{access_token}/telemetry"
)

payload = {
    "Actual_Temperature_C": 28.5,
    "humidity": 55.0,
    "state": "TEST",
    "cloudSource": "raspberrypi",
}

print("=" * 60)
print("ThingsBoard Telemetry Test")
print(f"Host: {thingsboard_host}")
print("Sending test telemetry...")
print("=" * 60)

try:
    response = requests.post(
        telemetry_url,
        json=payload,
        timeout=10,
    )

    if response.status_code in (200, 204):
        print("ThingsBoard upload: SUCCESS")
        print(f"HTTP status: {response.status_code}")
        print(f"Payload: {payload}")
    else:
        print("ThingsBoard upload: FAILED")
        print(f"HTTP status: {response.status_code}")
        print(f"Response: {response.text}")

except requests.Timeout:
    print("ThingsBoard upload: TIMEOUT")

except requests.ConnectionError as error:
    print("ThingsBoard connection failed.")
    print(error)

except requests.RequestException as error:
    print(f"ThingsBoard request failed: {error}")
