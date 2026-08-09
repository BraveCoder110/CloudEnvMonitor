"""
fan_controller.py

Infrared fan controller using Linux ir-ctl.

Remote protocol:
    NEC

Learned commands:
    POWER       -> 0x45
    SPEED_UP    -> 0x15
    SPEED_DOWN  -> 0x18
    OSCILLATION -> 0x07

Optimization:
Instead of sleeping AFTER every IR command, the controller
only enforces a minimum interval BEFORE the next command.

This preserves reliable IR command spacing while avoiding
an unnecessary delay after the final command.
"""

import subprocess
import time


class FanController:
    IR_DEVICE = "/dev/lirc0"

    POWER_CODE = "nec:0x45"
    SPEED_UP_CODE = "nec:0x15"
    SPEED_DOWN_CODE = "nec:0x18"
    OSCILLATION_CODE = "nec:0x07"

    # Minimum interval between two IR commands.
    MIN_COMMAND_GAP_SECONDS = 0.5

    def __init__(self) -> None:
        # Software-estimated state.
        #
        # Important:
        # The physical fan provides no feedback.
        # Therefore the fan must physically be OFF when
        # the application starts.
        self.power_on = False
        self.speed_level = 1
        self.oscillation_on = False

        self._last_ir_command_time = None

    def _wait_for_command_gap(
            self,
    ) -> None:
        """
        Ensure sufficient spacing between consecutive
        infrared commands.

        There is no delay after the FINAL command.
        """

        if self._last_ir_command_time is None:
            return

        elapsed = (
                time.perf_counter()
                - self._last_ir_command_time
        )

        remaining = (
                self.MIN_COMMAND_GAP_SECONDS
                - elapsed
        )

        if remaining > 0:
            time.sleep(
                remaining
            )

    def _send_ir(
            self,
            code: str,
    ) -> bool:
        """
        Send one NEC infrared command.
        """

        self._wait_for_command_gap()

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

            if result.returncode != 0:
                print(
                    "IR send failed:",
                    result.stderr.strip(),
                )
                return False

            # Record the time when this IR command has
            # successfully completed.
            self._last_ir_command_time = (
                time.perf_counter()
            )

            return True

        except subprocess.TimeoutExpired:
            print(
                "IR send timeout."
            )
            return False

        except Exception as error:
            print(
                "IR send exception:",
                type(error).__name__,
                error,
            )
            return False

    def turn_on(self) -> bool:
        if self.power_on:
            print(
                "Fan already ON."
            )
            return True

        print(
            "Sending FAN POWER ON..."
        )

        if not self._send_ir(
                self.POWER_CODE
        ):
            return False

        self.power_on = True
        self.speed_level = 1
        self.oscillation_on = False

        print(
            "Fan state: ON, "
            "assumed speed level 1."
        )

        return True

    def turn_off(self) -> bool:
        if not self.power_on:
            print(
                "Fan already OFF."
            )
            return True

        print(
            "Sending FAN POWER OFF..."
        )

        if not self._send_ir(
                self.POWER_CODE
        ):
            return False

        self.power_on = False
        self.speed_level = 1
        self.oscillation_on = False

        print(
            "Fan state: OFF."
        )

        return True

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

        target = (
                self.speed_level + 1
        )

        print(
            f"Fan speed: "
            f"{self.speed_level} -> {target}"
        )

        if not self._send_ir(
                self.SPEED_UP_CODE
        ):
            return False

        self.speed_level = target

        return True

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

        target = (
                self.speed_level - 1
        )

        print(
            f"Fan speed: "
            f"{self.speed_level} -> {target}"
        )

        if not self._send_ir(
                self.SPEED_DOWN_CODE
        ):
            return False

        self.speed_level = target

        return True

    def set_speed(
            self,
            target_level: int,
    ) -> bool:
        if target_level not in (
                1,
                2,
                3,
        ):
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

    def toggle_oscillation(
            self,
    ) -> bool:
        if not self.power_on:
            print(
                "Cannot toggle oscillation: "
                "fan is OFF."
            )
            return False

        print(
            "Toggling fan oscillation..."
        )

        if not self._send_ir(
                self.OSCILLATION_CODE
        ):
            return False

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

    def status(
            self,
    ) -> dict:
        return {
            "powerOn": self.power_on,
            "speedLevel": self.speed_level,
            "oscillationOn":
                self.oscillation_on,
        }