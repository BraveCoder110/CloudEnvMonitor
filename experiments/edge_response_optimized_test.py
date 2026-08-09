"""
Optimized Edge Response Time Experiment

This experiment evaluates the optimized actuator-control
architecture.

Optimizations:
1. LED executes immediately.
2. Buzzer executes asynchronously.
3. Fan cooling command is prioritized.
4. IR commands maintain a minimum safe command gap.
5. No unnecessary delay is added after the final IR command.

This measures Raspberry Pi actuator COMMAND latency.
It does not measure physical fan motor spin-up latency.
"""

import csv
import time
from datetime import datetime
from pathlib import Path

from hardware.buzzer_controller import (
    BuzzerController,
)
from hardware.fan_controller import (
    FanController,
)
from hardware.led_controller import (
    LEDController,
)


PROJECT_ROOT = (
        Path.home()
        / "azure-iot-environment"
)

RESULT_PATH = (
        PROJECT_ROOT
        / "experiments"
        / "results"
        / "edge_response_optimized.csv"
)


NUMBER_OF_TRIALS = 10

WAIT_BETWEEN_TRIALS_SECONDS = 3


def ensure_csv() -> None:
    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if RESULT_PATH.exists():
        return

    with RESULT_PATH.open(
            "w",
            newline="",
            encoding="utf-8",
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "trial",
                "timestamp",
                "led_latency_ms",
                "buzzer_start_latency_ms",
                "fan_power_latency_ms",
                "fan_level2_latency_ms",
                "total_control_latency_ms",
                "success",
            ]
        )


def run_trial(
        trial_number: int,
        led: LEDController,
        buzzer: BuzzerController,
        fan: FanController,
) -> None:

    print("\n" + "=" * 72)

    print(
        f"OPTIMIZED EDGE RESPONSE "
        f"- TRIAL {trial_number}"
    )

    print("=" * 72)

    # ------------------------------------------------------
    # Known initial state
    # ------------------------------------------------------

    led.off()
    buzzer.off()

    if fan.power_on:
        fan.turn_off()

    # Give the physical fan a little time to settle.
    time.sleep(1)

    print(
        "Starting optimized "
        "HIGH_TEMPERATURE event..."
    )

    # ------------------------------------------------------
    # Start timer
    # ------------------------------------------------------

    start_time = (
        time.perf_counter()
    )

    success = True

    # ------------------------------------------------------
    # LED - immediate local warning
    # ------------------------------------------------------

    led.alarm()

    led_done = (
        time.perf_counter()
    )

    # ------------------------------------------------------
    # Buzzer - NON-BLOCKING
    # ------------------------------------------------------

    buzzer_started = (
        buzzer.alarm_async(
            duration=0.5
        )
    )

    buzzer_start_done = (
        time.perf_counter()
    )

    if not buzzer_started:
        success = False

    # ------------------------------------------------------
    # Fan POWER gets priority.
    #
    # We do NOT wait for the buzzer to complete.
    # ------------------------------------------------------

    if not fan.turn_on():
        success = False

    fan_power_done = (
        time.perf_counter()
    )

    # ------------------------------------------------------
    # Set fan to level 2.
    #
    # FanController internally enforces the minimum
    # IR command spacing.
    # ------------------------------------------------------

    if not fan.set_speed(2):
        success = False

    fan_level2_done = (
        time.perf_counter()
    )

    # ------------------------------------------------------
    # Calculate command latencies
    # ------------------------------------------------------

    led_latency_ms = (
                             led_done
                             - start_time
                     ) * 1000

    buzzer_start_latency_ms = (
                                      buzzer_start_done
                                      - start_time
                              ) * 1000

    fan_power_latency_ms = (
                                   fan_power_done
                                   - start_time
                           ) * 1000

    fan_level2_latency_ms = (
                                    fan_level2_done
                                    - start_time
                            ) * 1000

    total_control_latency_ms = (
                                       fan_level2_done
                                       - start_time
                               ) * 1000

    # ------------------------------------------------------
    # Display
    # ------------------------------------------------------

    print(
        f"LED command latency       : "
        f"{led_latency_ms:.2f} ms"
    )

    print(
        f"Buzzer start latency      : "
        f"{buzzer_start_latency_ms:.2f} ms"
    )

    print(
        f"Fan power command latency : "
        f"{fan_power_latency_ms:.2f} ms"
    )

    print(
        f"Fan level-2 latency       : "
        f"{fan_level2_latency_ms:.2f} ms"
    )

    print(
        f"Total control latency     : "
        f"{total_control_latency_ms:.2f} ms"
    )

    print(
        f"Result                    : "
        f"{'SUCCESS' if success else 'FAILED'}"
    )

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------

    with RESULT_PATH.open(
            "a",
            newline="",
            encoding="utf-8",
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                trial_number,
                datetime.now().isoformat(),
                round(
                    led_latency_ms,
                    3,
                ),
                round(
                    buzzer_start_latency_ms,
                    3,
                ),
                round(
                    fan_power_latency_ms,
                    3,
                ),
                round(
                    fan_level2_latency_ms,
                    3,
                ),
                round(
                    total_control_latency_ms,
                    3,
                ),
                success,
            ]
        )

    # ------------------------------------------------------
    # Return to NORMAL
    # ------------------------------------------------------

    led.off()

    # Allow async buzzer to finish before next trial.
    time.sleep(0.6)

    buzzer.off()

    if fan.power_on:
        fan.turn_off()


def main() -> None:

    ensure_csv()

    led = LEDController()
    buzzer = BuzzerController()
    fan = FanController()

    print("=" * 72)

    print(
        "Optimized Edge Control "
        "Command Latency Experiment"
    )

    print(
        f"Trials: {NUMBER_OF_TRIALS}"
    )

    print(
        f"Output: {RESULT_PATH}"
    )

    print("=" * 72)

    try:

        for trial in range(
                1,
                NUMBER_OF_TRIALS + 1,
        ):

            run_trial(
                trial_number=trial,
                led=led,
                buzzer=buzzer,
                fan=fan,
            )

            if trial < NUMBER_OF_TRIALS:

                print(
                    f"\nWaiting "
                    f"{WAIT_BETWEEN_TRIALS_SECONDS} "
                    f"seconds..."
                )

                time.sleep(
                    WAIT_BETWEEN_TRIALS_SECONDS
                )

    except KeyboardInterrupt:

        print(
            "\nExperiment stopped by user."
        )

    finally:

        led.off()
        buzzer.off()

        if fan.power_on:
            fan.turn_off()

        led.close()
        buzzer.close()

        print(
            "\nExperiment finished."
        )

        print(
            f"Results saved to:\n"
            f"{RESULT_PATH}"
        )


if __name__ == "__main__":
    main()