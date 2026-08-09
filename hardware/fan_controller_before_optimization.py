import subprocess
import time


class FanController:
    """
    Infrared fan controller using Linux ir-ctl.

    Current remote codes:
        POWER       -> NEC 0x45
        SPEED_UP    -> NEC 0x15
        SPEED_DOWN  -> NEC 0x18
        OSCILLATION -> NEC 0x07
    """

    IR_DEVICE = "/dev/lirc0"

    POWER_CODE = "nec:0x45"
    SPEED_UP_CODE = "nec:0x15"
    SPEED_DOWN_CODE = "nec:0x18"
    OSCILLATION_CODE = "nec:0x07"

    COMMAND_DELAY_SECONDS = 0.5

    def __init__(self) -> None:
        # 软件状态，只代表树莓派“认为”的风扇状态。
        self.power_on = False
        self.speed_level = 1
        self.oscillation_on = False

    def _send_ir(self, code: str) -> bool:
        """
        Send one IR command using ir-ctl.
        """

        command = [
            "sudo",
            "ir-ctl",
            "-d",
            self.IR_DEVICE,
            "-S",
            code,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                time.sleep(
                    self.COMMAND_DELAY_SECONDS
                )
                return True

            print(
                "IR send failed:",
                result.stderr.strip(),
            )
            return False

        except subprocess.TimeoutExpired:
            print("IR send timeout.")
            return False

        except Exception as error:
            print(
                "IR send exception:",
                type(error).__name__,
                error,
            )
            return False

    def turn_on(self) -> bool:
        """
        Turn fan on if software state says it is off.
        """

        if self.power_on:
            print("Fan already ON.")
            return True

        print("Sending FAN POWER ON...")

        if self._send_ir(
                self.POWER_CODE
        ):
            self.power_on = True
            self.speed_level = 1

            print(
                "Fan state: ON, "
                "assumed speed level 1."
            )
            return True

        return False

    def turn_off(self) -> bool:
        """
        Turn fan off if software state says it is on.
        """

        if not self.power_on:
            print("Fan already OFF.")
            return True

        print("Sending FAN POWER OFF...")

        if self._send_ir(
                self.POWER_CODE
        ):
            self.power_on = False
            self.speed_level = 1
            self.oscillation_on = False

            print("Fan state: OFF.")
            return True

        return False

    def speed_up(self) -> bool:
        if not self.power_on:
            print(
                "Cannot increase speed: "
                "fan is OFF."
            )
            return False

        if self.speed_level >= 3:
            print(
                "Fan already at level 3."
            )
            return True

        print(
            f"Fan speed: "
            f"{self.speed_level} -> "
            f"{self.speed_level + 1}"
        )

        if self._send_ir(
                self.SPEED_UP_CODE
        ):
            self.speed_level += 1
            return True

        return False

    def speed_down(self) -> bool:
        if not self.power_on:
            print(
                "Cannot decrease speed: "
                "fan is OFF."
            )
            return False

        if self.speed_level <= 1:
            print(
                "Fan already at level 1."
            )
            return True

        print(
            f"Fan speed: "
            f"{self.speed_level} -> "
            f"{self.speed_level - 1}"
        )

        if self._send_ir(
                self.SPEED_DOWN_CODE
        ):
            self.speed_level -= 1
            return True

        return False

    def set_speed(
            self,
            target_level: int,
    ) -> bool:
        if target_level not in (1, 2, 3):
            print(
                "Invalid fan speed level. "
                "Use 1, 2, or 3."
            )
            return False

        if not self.power_on:
            if not self.turn_on():
                return False

        while (
                self.speed_level
                < target_level
        ):
            if not self.speed_up():
                return False

        while (
                self.speed_level
                > target_level
        ):
            if not self.speed_down():
                return False

        print(
            f"Fan target speed reached: "
            f"level {self.speed_level}"
        )

        return True

    def toggle_oscillation(self) -> bool:
        if not self.power_on:
            print(
                "Cannot toggle oscillation: "
                "fan is OFF."
            )
            return False

        print(
            "Toggling fan oscillation..."
        )

        if self._send_ir(
                self.OSCILLATION_CODE
        ):
            self.oscillation_on = (
                not self.oscillation_on
            )

            print(
                "Oscillation:",
                "ON"
                if self.oscillation_on
                else "OFF",
            )

            return True

        return False

    def status(self) -> dict:
        return {
            "powerOn": self.power_on,
            "speedLevel": self.speed_level,
            "oscillationOn": (
                self.oscillation_on
            ),
        }