"""
buzzer_controller.py

Active buzzer controller.

Optimized version:
- alarm() remains available for blocking tests.
- alarm_async() performs the beep in a background thread.
- Edge control no longer needs to wait for the buzzer to finish.
"""

import threading
import time

from gpiozero import Buzzer


class BuzzerController:
    def __init__(
            self,
            gpio_pin: int = 18,
    ) -> None:
        self.buzzer = Buzzer(gpio_pin)

        # Prevent multiple alarm threads from starting
        # at the same time.
        self._lock = threading.Lock()

        self._alarm_thread = None

    def alarm(
            self,
            duration: float = 0.5,
    ) -> None:
        """
        Blocking alarm.

        Kept for hardware tests where blocking behaviour
        is acceptable.
        """

        with self._lock:
            self.buzzer.on()
            time.sleep(duration)
            self.buzzer.off()

    def _alarm_worker(
            self,
            duration: float,
    ) -> None:
        """
        Internal background alarm worker.
        """

        with self._lock:
            try:
                self.buzzer.on()
                time.sleep(duration)

            finally:
                self.buzzer.off()

    def alarm_async(
            self,
            duration: float = 0.5,
    ) -> bool:
        """
        Start a non-blocking buzzer alarm.

        Returns True if a new alarm was started.

        Returns False if an alarm is already running.
        """

        if (
                self._alarm_thread is not None
                and self._alarm_thread.is_alive()
        ):
            return False

        self._alarm_thread = threading.Thread(
            target=self._alarm_worker,
            args=(duration,),
            name="buzzer-alarm-thread",
            daemon=True,
        )

        self._alarm_thread.start()

        return True

    def off(self) -> None:
        self.buzzer.off()

    def close(self) -> None:
        """
        Safely release the buzzer.

        If an asynchronous beep is still running,
        wait briefly for it to finish.
        """

        if (
                self._alarm_thread is not None
                and self._alarm_thread.is_alive()
        ):
            self._alarm_thread.join(
                timeout=1.0
            )

        self.buzzer.off()
        self.buzzer.close()