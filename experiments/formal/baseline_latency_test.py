"""
Formal Baseline Edge-Control Latency Experiment

Condition:
    Sequential blocking actuator control.

IMPORTANT:
This script intentionally imports the frozen
pre-optimization actuator implementations.

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

from hardware.buzzer_controller_before_optimization import (
    BuzzerController,
)
from hardware.fan_controller_before_optimization import (
    FanController,
)
from hardware.led_controller import LEDController


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
            / f"baseline_session_{session_id}.csv"
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
            f"{result_path}\n"
            f"Delete it manually only if you really "
            f"want to repeat this session."
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
                "buzzer_complete_latency_ms",
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
        f"BASELINE | SESSION {session_id} | "
        f"TRIAL {trial_number}/{NUMBER_OF_TRIALS}"
    )

    print("=" * 72)

    # Known initial state
    led.off()
    buzzer.off()

    if fan.power_on:
        fan.turn_off()

    time.sleep(1)

    success = True

    # High-temperature decision is assumed to have
    # happened exactly here.
    start = time.perf_counter()

    # LED
    led.alarm()
    led_done = time.perf_counter()

    # Blocking buzzer
    buzzer.alarm(
        duration=0.5
    )
    buzzer_done = time.perf_counter()

    # Fan power
    if not fan.turn_on():
        success = False

    fan_power_done = time.perf_counter()

    # Fan target = level 2
    if not fan.set_speed(2):
        success = False

    fan_level2_done = time.perf_counter()

    led_latency = (
                          led_done - start
                  ) * 1000

    buzzer_latency = (
                             buzzer_done - start
                     ) * 1000

    fan_power_latency = (
                                fan_power_done - start
                        ) * 1000

    fan_level2_latency = (
                                 fan_level2_done - start
                         ) * 1000

    total_latency = fan_level2_latency

    print(
        f"LED                 : "
        f"{led_latency:.3f} ms"
    )

    print(
        f"Buzzer complete     : "
        f"{buzzer_latency:.3f} ms"
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
                "baseline",
                session_id,
                trial_number,
                datetime.now().isoformat(),
                round(led_latency, 3),
                round(buzzer_latency, 3),
                round(fan_power_latency, 3),
                round(fan_level2_latency, 3),
                round(total_latency, 3),
                success,
            ]
        )

    # Return to normal state
    led.off()
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
    print("Condition : BASELINE")
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
            "\nFormal baseline session completed."
        )


if __name__ == "__main__":
    main()