import time

from hardware.fan_controller import (
    FanController,
)


def main() -> None:
    fan = FanController()

    print("=" * 60)
    print("Fan Controller Test")
    print("=" * 60)

    print("\n1. Turn fan ON")
    fan.turn_on()
    print(fan.status())

    time.sleep(2)

    print("\n2. Increase to speed level 2")
    fan.set_speed(2)
    print(fan.status())

    time.sleep(2)

    print("\n3. Increase to speed level 3")
    fan.set_speed(3)
    print(fan.status())

    time.sleep(2)

    print("\n4. Decrease to speed level 1")
    fan.set_speed(1)
    print(fan.status())

    time.sleep(2)

    print("\n5. Toggle oscillation")
    fan.toggle_oscillation()
    print(fan.status())

    time.sleep(2)

    print("\n6. Turn fan OFF")
    fan.turn_off()
    print(fan.status())

    print("\nFan controller test completed.")


if __name__ == "__main__":
    main()