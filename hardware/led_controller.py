from gpiozero import LED


class LEDController:
    def __init__(
            self,
            gpio_pin: int = 17,
    ) -> None:
        self.led = LED(gpio_pin)

    def normal(self) -> None:
        # Normal state: LED off
        self.led.off()

    def alarm(self) -> None:
        # High-temperature state: LED on
        self.led.on()

    def off(self) -> None:
        self.led.off()

    def close(self) -> None:
        self.led.off()
        self.led.close()