"""
Edge Response Time Experiment

Purpose
-------
Measure the software-side edge control latency when the
temperature condition changes into HIGH_TEMPERATURE.

Important
---------
This experiment measures command-processing latency on the
Raspberry Pi.

It does NOT claim to measure the physical motor spin-up time
of the fan because the fan does not provide feedback.

Output
------
experiments/results/edge_response.csv
"""

import csv
import time
from datetime import datetime
from pathlib import Path

from hardware.buzzer_controller import BuzzerController
from hardware.fan_controller import FanController
from hardware.led_controller import LEDController


PROJECT_ROOT = (
        Path.home()
        / "azure-iot-environment"
)

RESULT_PATH = (
        PROJECT_ROOT
        / "experiments"
        / "results"
        / "edge_response.csv"
)


NUMBER_OF_TRIALS = 10
WAIT_BETWEEN_TRIALS_SECONDS = 3


def ensure_csv() -> None:
    """
    Create the result CSV with a header if it does not exist.
    """

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

        writer = csv.writer(file)

        writer.writerow(
            [
                "trial",
                "timestamp",
                "led_latency_ms",
                "buzzer_latency_ms",
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

    print("\n" + "=" * 70)
    print(
        f"EDGE RESPONSE EXPERIMENT "
        f"- TRIAL {trial_number}"
    )
    print("=" * 70)

    # -------------------------------------------------------
    # Each experiment must begin from a known state.
    # -------------------------------------------------------

    led.off()
    buzzer.off()

    if fan.power_on:
        fan.turn_off()

    time.sleep(1)

    print(
        "Make sure the physical fan is OFF."
    )

    print(
        "Starting simulated HIGH_TEMPERATURE "
        "edge event..."
    )

    # -------------------------------------------------------
    # Start timing.
    #
    # This represents the moment the edge controller has
    # determined that a high-temperature event exists.
    # -------------------------------------------------------

    start_time = time.perf_counter()

    success = True

    # -------------------------------------------------------
    # LED
    # -------------------------------------------------------

    led.alarm()

    led_done = time.perf_counter()

    # -------------------------------------------------------
    # Buzzer
    # -------------------------------------------------------

    buzzer.alarm(
        duration=0.5
    )

    buzzer_done = time.perf_counter()

    # -------------------------------------------------------
    # Fan power
    # -------------------------------------------------------

    if not fan.turn_on():
        success = False

    fan_power_done = time.perf_counter()

    # -------------------------------------------------------
    # Fan target level = 2
    # -------------------------------------------------------

    if not fan.set_speed(2):
        success = False

    fan_level2_done = time.perf_counter()

    # -------------------------------------------------------
    # Calculate latency
    # -------------------------------------------------------

    led_latency_ms = (
                             led_done
                             - start_time
                     ) * 1000

    buzzer_latency_ms = (
                                buzzer_done
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

    total_latency_ms = (
                               fan_level2_done
                               - start_time
                       ) * 1000

    # -------------------------------------------------------
    # Print result
    # -------------------------------------------------------

    print(
        f"LED command latency       : "
        f"{led_latency_ms:.2f} ms"
    )

    print(
        f"Buzzer complete latency   : "
        f"{buzzer_latency_ms:.2f} ms"
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
        f"{total_latency_ms:.2f} ms"
    )

    print(
        f"Result                    : "
        f"{'SUCCESS' if success else 'FAILED'}"
    )

    # -------------------------------------------------------
    # Save result
    # -------------------------------------------------------

    with RESULT_PATH.open(
            "a",
            newline="",
            encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                trial_number,
                datetime.now().isoformat(),
                round(
                    led_latency_ms,
                    3,
                ),
                round(
                    buzzer_latency_ms,
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
                    total_latency_ms,
                    3,
                ),
                success,
            ]
        )

    # -------------------------------------------------------
    # Return system to NORMAL
    # -------------------------------------------------------

    led.off()
    buzzer.off()

    if fan.power_on:
        fan.turn_off()


def main() -> None:

    ensure_csv()

    led = LEDController()

    buzzer = BuzzerController()

    fan = FanController()

    print("=" * 70)

    print(
        "Edge Control Command Latency Experiment"
    )

    print(
        f"Trials: {NUMBER_OF_TRIALS}"
    )

    print(
        f"Output: {RESULT_PATH}"
    )

    print("=" * 70)

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