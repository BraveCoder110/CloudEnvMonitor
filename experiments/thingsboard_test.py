import requests
import random
import time

url = "https://thingsboard.cloud/api/v1/nbvxd094sw236rr7i2kk/telemetry"

headers = {
    "Content-Type": "text/plain"
}

while True:
    temperature = round(random.uniform(28.0, 32.0), 2)

    data = {
        "Actual_Temperature_C": f"{temperature:.2f}"
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=10
        )

        print(
            f"发送温度: {temperature:.2f} °C | "
            f"HTTP状态码: {response.status_code} | "
            f"响应: {response.text}"
        )

    except requests.RequestException as e:
        print(f"请求失败: {e}")

    time.sleep(2)