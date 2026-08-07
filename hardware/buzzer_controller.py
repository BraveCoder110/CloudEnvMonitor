import time

from gpiozero import Buzzer


class BuzzerController:
    def __init__(
            self,
            gpio_pin: int = 18,
    ) -> None:
        self.buzzer = Buzzer(gpio_pin)

    def alarm(
            self,
            duration: float = 0.2,
    ) -> None:
        self.buzzer.on()
        time.sleep(duration)
        self.buzzer.off()

    def off(self) -> None:
        self.buzzer.off()

    def close(self) -> None:
        self.buzzer.off()
        self.buzzer.close()