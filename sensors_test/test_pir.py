import time
from datetime import datetime

from gpiozero import MotionSensor


PIR_GPIO = 23
WARM_UP_SECONDS = 30


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    pir = MotionSensor(
        PIR_GPIO,
        pull_up=False,
        queue_len=5,
        sample_rate=10,
        threshold=0.5,
    )

    print("=" * 58)
    print("PIR Motion Sensor Test")
    print("PIR OUT: GPIO23 / physical Pin 16")
    print(f"Warm-up time: {WARM_UP_SECONDS} seconds")
    print("Press Ctrl+C to stop")
    print("=" * 58)

    try:
        for remaining in range(WARM_UP_SECONDS, 0, -1):
            print(
                f"\rPIR warming up... {remaining:02d} seconds remaining",
                end="",
                flush=True,
            )
            time.sleep(1)

        print("\nPIR warm-up completed.")
        print("Stand still first, then move your hand in front of the sensor.")

        previous_state: bool | None = None

        i=0
        while True:
            i+=1
            print(f"---{i}----")
            motion_detected = pir.motion_detected

            if motion_detected != previous_state:
                if motion_detected:
                    print(f"[{timestamp()}] MOTION DETECTED")
                else:
                    print(f"[{timestamp()}] NO MOTION")

                previous_state = motion_detected

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nPIR test stopped by user.")

    finally:
        pir.close()
        print("PIR GPIO resource released safely.")


if __name__ == "__main__":
    main()
