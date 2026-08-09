"""
Formal Optimized Edge-Control Latency Experiment

Condition:
    Non-blocking buzzer +
    priority fan control +
    optimized IR command spacing.

Trials per session:
    30

This experiment measures actuator COMMAND latency,
not physical fan motor spin-up latency.
"""

import argparse
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


PROJECT_ROOT = Path.home() / "azure-iot-environment"

NUMBER_OF_TRIALS = 30
WAIT_BETWEEN_TRIALS_SECONDS = 3


def get_result_path(
        session_id: int,
) -> Path:

    return (
            PROJECT_ROOT
            / "experiments"
            / "results"
            / "formal"
            / f"optimized_session_{session_id}.csv"
    )


def create_csv(
        result_path: Path,
) -> None:

    result_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if result_path.exists():
        raise RuntimeError(
            f"Result file already exists:\n"
            f"{result_path}"
        )

    with result_path.open(
            "w",
            newline="",
            encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "condition",
                "session",
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
        session_id: int,
        trial_number: int,
        result_path: Path,
        led: LEDController,
        buzzer: BuzzerController,
        fan: FanController,
) -> None:

    print("\n" + "=" * 72)

    print(
        f"OPTIMIZED | SESSION {session_id} | "
        f"TRIAL {trial_number}/{NUMBER_OF_TRIALS}"
    )

    print("=" * 72)

    led.off()
    buzzer.off()

    if fan.power_on:
        fan.turn_off()

    time.sleep(1)

    success = True

    start = time.perf_counter()

    # Immediate LED warning
    led.alarm()
    led_done = time.perf_counter()

    # Non-blocking audible alarm
    buzzer_started = (
        buzzer.alarm_async(
            duration=0.5
        )
    )

    buzzer_started_done = (
        time.perf_counter()
    )

    if not buzzer_started:
        success = False

    # Cooling actuator immediately receives priority
    if not fan.turn_on():
        success = False

    fan_power_done = (
        time.perf_counter()
    )

    if not fan.set_speed(2):
        success = False

    fan_level2_done = (
        time.perf_counter()
    )

    led_latency = (
                          led_done - start
                  ) * 1000

    buzzer_start_latency = (
                                   buzzer_started_done - start
                           ) * 1000

    fan_power_latency = (
                                fan_power_done - start
                        ) * 1000

    fan_level2_latency = (
                                 fan_level2_done - start
                         ) * 1000

    total_latency = (
        fan_level2_latency
    )

    print(
        f"LED                 : "
        f"{led_latency:.3f} ms"
    )

    print(
        f"Buzzer start        : "
        f"{buzzer_start_latency:.3f} ms"
    )

    print(
        f"Fan POWER           : "
        f"{fan_power_latency:.3f} ms"
    )

    print(
        f"Fan Level 2         : "
        f"{fan_level2_latency:.3f} ms"
    )

    print(
        f"Total               : "
        f"{total_latency:.3f} ms"
    )

    print(
        f"Success             : "
        f"{success}"
    )

    with result_path.open(
            "a",
            newline="",
            encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "optimized",
                session_id,
                trial_number,
                datetime.now().isoformat(),
                round(led_latency, 3),
                round(
                    buzzer_start_latency,
                    3,
                ),
                round(
                    fan_power_latency,
                    3,
                ),
                round(
                    fan_level2_latency,
                    3,
                ),
                round(
                    total_latency,
                    3,
                ),
                success,
            ]
        )

    led.off()

    # Allow asynchronous beep to finish.
    time.sleep(0.6)

    buzzer.off()

    if fan.power_on:
        fan.turn_off()


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--session",
        type=int,
        required=True,
        choices=[1, 2, 3],
    )

    args = parser.parse_args()

    session_id = args.session

    result_path = get_result_path(
        session_id
    )

    create_csv(
        result_path
    )

    led = LEDController()
    buzzer = BuzzerController()
    fan = FanController()

    print("=" * 72)
    print("FORMAL EDGE LATENCY EXPERIMENT")
    print("Condition : OPTIMIZED")
    print(f"Session   : {session_id}")
    print(f"Trials    : {NUMBER_OF_TRIALS}")
    print(f"Output    : {result_path}")
    print("=" * 72)

    try:

        for trial in range(
                1,
                NUMBER_OF_TRIALS + 1,
        ):

            run_trial(
                session_id=session_id,
                trial_number=trial,
                result_path=result_path,
                led=led,
                buzzer=buzzer,
                fan=fan,
            )

            if trial < NUMBER_OF_TRIALS:
                time.sleep(
                    WAIT_BETWEEN_TRIALS_SECONDS
                )

    finally:

        led.off()
        buzzer.off()

        if fan.power_on:
            fan.turn_off()

        led.close()
        buzzer.close()

        print(
            "\nFormal optimized session completed."
        )


if __name__ == "__main__":
    main()