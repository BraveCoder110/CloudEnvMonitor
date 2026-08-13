"""
E4 Scalability Monitor V1
=========================

Experiment:
Offline Backlog Scalability of Dual-Cloud Recovery

Research question:
How does historical offline backlog size affect recovery time
and effective backfill throughput for Azure IoT Hub and
ThingsBoard?

Backlog levels:
    10 records
    30 records
    60 records

Each level is repeated across three formal sessions.

Important design:
- Raspberry Pi remains offline while backlog is accumulated.
- The monitor freezes a historical cutoff Record ID.
- Only records with id <= cutoff_record_id are measured.
- New telemetry generated after reconnection is excluded.
- Timing begins at T0 when network restoration is commanded.
"""

import argparse
import csv
import sqlite3
import time
from datetime import datetime
from pathlib import Path


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
        Path.home()
        / "azure-iot-environment"
)

DATABASE_PATH = (
        PROJECT_ROOT
        / "database"
        / "environment.db"
)

RESULT_DIR = (
        PROJECT_ROOT
        / "experiments"
        / "results"
        / "e4"
)


# ============================================================
# Configuration
# ============================================================

VALID_BACKLOG_TARGETS = [
    10,
    30,
    60,
]

DEFAULT_TOLERANCE = 2

DEFAULT_COUNTDOWN = 5

POLL_INTERVAL_SECONDS = 0.2

MAX_MONITOR_SECONDS = 300


# ============================================================
# Helpers
# ============================================================

def now_iso():
    return (
        datetime.now()
        .astimezone()
        .isoformat()
    )


def get_max_record_id():

    with sqlite3.connect(
            DATABASE_PATH
    ) as connection:

        value = connection.execute(
            """
            SELECT MAX(id)
            FROM telemetry
            """
        ).fetchone()[0]

    return (
        int(value)
        if value is not None
        else 0
    )


def get_historical_pending(
        cutoff_record_id,
):

    with sqlite3.connect(
            DATABASE_PATH
    ) as connection:

        azure = connection.execute(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE id <= ?
              AND azure_status = 'pending'
            """,
            (
                cutoff_record_id,
            ),
        ).fetchone()[0]

        thingsboard = connection.execute(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE id <= ?
              AND thingsboard_status = 'pending'
            """,
            (
                cutoff_record_id,
            ),
        ).fetchone()[0]

    return {
        "azure": int(azure),
        "thingsboard": int(
            thingsboard
        ),
    }


def save_result(
        path,
        row,
):

    with path.open(
            "w",
            encoding="utf-8",
            newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                row.keys()
            ),
        )

        writer.writeheader()
        writer.writerow(row)


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--backlog",
        type=int,
        required=True,
        choices=VALID_BACKLOG_TARGETS,
        help=(
            "Target historical backlog size."
        ),
    )

    parser.add_argument(
        "--session",
        type=int,
        required=True,
        choices=[
            1,
            2,
            3,
        ],
    )

    parser.add_argument(
        "--tolerance",
        type=int,
        default=DEFAULT_TOLERANCE,
        help=(
            "Maximum allowed backlog overshoot."
        ),
    )

    parser.add_argument(
        "--countdown",
        type=int,
        default=DEFAULT_COUNTDOWN,
    )

    args = parser.parse_args()

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path = (
            RESULT_DIR
            / (
                f"e4_backlog_{args.backlog}"
                f"_session_{args.session}.csv"
            )
    )

    if result_path.exists():

        raise RuntimeError(
            "\nFormal E4 result file already exists:\n"
            f"{result_path}\n\n"
            "Rename or remove it manually before "
            "repeating the trial."
        )

    # ========================================================
    # Freeze historical workload
    # ========================================================

    cutoff_record_id = (
        get_max_record_id()
    )

    initial = (
        get_historical_pending(
            cutoff_record_id
        )
    )

    azure_initial = (
        initial["azure"]
    )

    tb_initial = (
        initial["thingsboard"]
    )

    upper_limit = (
            args.backlog
            + args.tolerance
    )

    print("=" * 76)

    print(
        "E4 OFFLINE BACKLOG SCALABILITY MONITOR V1"
    )

    print("=" * 76)

    print(
        f"Backlog target             : "
        f"{args.backlog}"
    )

    print(
        f"Session                    : "
        f"{args.session}"
    )

    print(
        f"Allowed backlog range      : "
        f"{args.backlog} - {upper_limit}"
    )

    print(
        f"Cutoff Record ID           : "
        f"{cutoff_record_id}"
    )

    print(
        f"Initial Azure backlog      : "
        f"{azure_initial}"
    )

    print(
        f"Initial ThingsBoard backlog: "
        f"{tb_initial}"
    )

    print("=" * 76)

    # ========================================================
    # Validate workload
    # ========================================================

    if (
            azure_initial
            < args.backlog
            or tb_initial
            < args.backlog
    ):

        raise RuntimeError(
            "\nE4 experiment NOT started.\n\n"
            "Insufficient backlog.\n"
            f"Target >= {args.backlog}\n"
            f"Azure = {azure_initial}\n"
            f"ThingsBoard = {tb_initial}\n\n"
            "Keep Raspberry Pi offline and allow "
            "main.py to generate more records."
        )

    if (
            azure_initial
            > upper_limit
            or tb_initial
            > upper_limit
    ):

        raise RuntimeError(
            "\nE4 experiment NOT started.\n\n"
            "Backlog exceeded formal tolerance.\n"
            f"Allowed maximum = {upper_limit}\n"
            f"Azure = {azure_initial}\n"
            f"ThingsBoard = {tb_initial}\n\n"
            "This workload should not be used as a "
            "formal scalability trial."
        )

    print()

    print(
        "Backlog validation: PASS"
    )

    print()

    print(
        "KEEP RASPBERRY PI OFFLINE."
    )

    print(
        "Do NOT restore networking during countdown."
    )

    print()

    # ========================================================
    # Countdown
    # ========================================================

    for remaining in range(
            args.countdown,
            0,
            -1,
    ):

        print(
            f"Network restore command "
            f"in {remaining}..."
        )

        time.sleep(1)

    # ========================================================
    # T0
    # ========================================================

    started_at = (
        now_iso()
    )

    start_time = (
        time.perf_counter()
    )

    print()

    print("=" * 76)

    print(
        "T0 — RESTORE RASPBERRY PI NETWORK NOW"
    )

    print("=" * 76)

    print(
        f"Timer started at: "
        f"{started_at}"
    )

    print()

    # ========================================================
    # Measurements
    # ========================================================

    azure_first_progress = None
    tb_first_progress = None

    azure_recovery = None
    tb_recovery = None

    previous_azure = (
        azure_initial
    )

    previous_tb = (
        tb_initial
    )

    while True:

        elapsed = (
                time.perf_counter()
                - start_time
        )

        current = (
            get_historical_pending(
                cutoff_record_id
            )
        )

        azure_pending = (
            current["azure"]
        )

        tb_pending = (
            current[
                "thingsboard"
            ]
        )

        # ----------------------------------------------------
        # First progress
        # ----------------------------------------------------

        if (
                azure_first_progress
                is None
                and azure_pending
                < azure_initial
        ):

            azure_first_progress = (
                elapsed
            )

            print(
                f"[{elapsed:8.3f}s] "
                f"Azure first progress: "
                f"{azure_initial} -> "
                f"{azure_pending}"
            )

        if (
                tb_first_progress
                is None
                and tb_pending
                < tb_initial
        ):

            tb_first_progress = (
                elapsed
            )

            print(
                f"[{elapsed:8.3f}s] "
                f"ThingsBoard first progress: "
                f"{tb_initial} -> "
                f"{tb_pending}"
            )

        # ----------------------------------------------------
        # Queue changes
        # ----------------------------------------------------

        if (
                azure_pending
                != previous_azure
        ):

            print(
                f"[{elapsed:8.3f}s] "
                f"Azure historical pending: "
                f"{azure_pending}"
            )

            previous_azure = (
                azure_pending
            )

        if (
                tb_pending
                != previous_tb
        ):

            print(
                f"[{elapsed:8.3f}s] "
                f"ThingsBoard historical pending: "
                f"{tb_pending}"
            )

            previous_tb = (
                tb_pending
            )

        # ----------------------------------------------------
        # Recovery complete
        # ----------------------------------------------------

        if (
                azure_recovery
                is None
                and azure_pending == 0
        ):

            azure_recovery = (
                elapsed
            )

            print()

            print(
                f"[{elapsed:8.3f}s] "
                "AZURE HISTORICAL BACKLOG CLEARED"
            )

        if (
                tb_recovery
                is None
                and tb_pending == 0
        ):

            tb_recovery = (
                elapsed
            )

            print()

            print(
                f"[{elapsed:8.3f}s] "
                "THINGSBOARD HISTORICAL "
                "BACKLOG CLEARED"
            )

        if (
                azure_recovery
                is not None
                and tb_recovery
                is not None
        ):
            break

        if (
                elapsed
                >= MAX_MONITOR_SECONDS
        ):

            print()

            print(
                "Maximum monitoring time reached."
            )

            break

        time.sleep(
            POLL_INTERVAL_SECONDS
        )

    # ========================================================
    # Calculate results
    # ========================================================

    finished_at = (
        now_iso()
    )

    monitor_duration = (
            time.perf_counter()
            - start_time
    )

    azure_throughput = None

    if (
            azure_recovery
            is not None
            and azure_recovery > 0
    ):

        azure_throughput = (
                azure_initial
                / azure_recovery
        )

    tb_throughput = None

    if (
            tb_recovery
            is not None
            and tb_recovery > 0
    ):

        tb_throughput = (
                tb_initial
                / tb_recovery
        )

    success = (
            azure_recovery
            is not None
            and tb_recovery
            is not None
    )

    row = {
        "target_backlog":
            args.backlog,

        "session":
            args.session,

        "cutoff_record_id":
            cutoff_record_id,

        "initial_azure_backlog":
            azure_initial,

        "initial_thingsboard_backlog":
            tb_initial,

        "started_at":
            started_at,

        "finished_at":
            finished_at,

        "azure_first_progress_s":
            (
                round(
                    azure_first_progress,
                    3,
                )
                if azure_first_progress
                   is not None
                else ""
            ),

        "thingsboard_first_progress_s":
            (
                round(
                    tb_first_progress,
                    3,
                )
                if tb_first_progress
                   is not None
                else ""
            ),

        "azure_recovery_s":
            (
                round(
                    azure_recovery,
                    3,
                )
                if azure_recovery
                   is not None
                else ""
            ),

        "thingsboard_recovery_s":
            (
                round(
                    tb_recovery,
                    3,
                )
                if tb_recovery
                   is not None
                else ""
            ),

        "azure_effective_throughput_rps":
            (
                round(
                    azure_throughput,
                    4,
                )
                if azure_throughput
                   is not None
                else ""
            ),

        "thingsboard_effective_throughput_rps":
            (
                round(
                    tb_throughput,
                    4,
                )
                if tb_throughput
                   is not None
                else ""
            ),

        "monitor_duration_s":
            round(
                monitor_duration,
                3,
            ),

        "result":
            (
                "PASS"
                if success
                else "FAIL"
            ),
    }

    save_result(
        result_path,
        row,
    )

    # ========================================================
    # Console summary
    # ========================================================

    print()

    print("=" * 76)

    print(
        "E4 FORMAL RESULT"
    )

    print("=" * 76)

    print(
        f"Backlog target              : "
        f"{args.backlog}"
    )

    print(
        f"Actual Azure backlog        : "
        f"{azure_initial}"
    )

    print(
        f"Actual ThingsBoard backlog  : "
        f"{tb_initial}"
    )

    print()

    if azure_recovery is not None:

        print(
            f"Azure recovery              : "
            f"{azure_recovery:.3f} s"
        )

    else:

        print(
            "Azure recovery              : FAILED"
        )

    if tb_recovery is not None:

        print(
            f"ThingsBoard recovery        : "
            f"{tb_recovery:.3f} s"
        )

    else:

        print(
            "ThingsBoard recovery        : FAILED"
        )

    print()

    if azure_throughput is not None:

        print(
            f"Azure effective throughput  : "
            f"{azure_throughput:.4f} records/s"
        )

    if tb_throughput is not None:

        print(
            f"TB effective throughput     : "
            f"{tb_throughput:.4f} records/s"
        )

    print()

    print(
        f"Overall result              : "
        f"{row['result']}"
    )

    print()

    print(
        f"Saved to:\n"
        f"{result_path}"
    )


if __name__ == "__main__":
    main()