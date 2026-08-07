from time import sleep

from gpiozero import Buzzer


BUZZER_GPIO = 18


def main() -> None:
    buzzer = Buzzer(BUZZER_GPIO)

    print("=" * 45)
    print("Active buzzer test")
    print("GPIO18 / physical Pin 12")
    print("The buzzer should sound three times.")
    print("=" * 45)

    try:
        for number in range(1, 4):
            print(f"Beep {number}: ON")
            buzzer.on()
            sleep(0.2)

            print(f"Beep {number}: OFF")
            buzzer.off()
            sleep(0.8)

        print("Buzzer test completed successfully.")

    except KeyboardInterrupt:
        print("\nTest stopped by user.")

    finally:
        buzzer.off()
        buzzer.close()
        print("Buzzer switched off safely.")


if __name__ == "__main__":
    main()
