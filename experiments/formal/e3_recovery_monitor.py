"""
E3 Recovery Monitor V2
======================

Experiment:
Dual-Cloud Recovery & Backfill Performance

Purpose
-------
Measure end-to-end recovery time of a frozen historical
offline backlog after network connectivity is restored.

Cloud targets:
1. Microsoft Azure IoT Hub
2. ThingsBoard

Experimental design
-------------------
1. Raspberry Pi is disconnected from the real network.
2. main.py continues generating telemetry into SQLite.
3. Both cloud queues must accumulate at least 20 records.
4. Before reconnection, this script freezes a cutoff Record ID.
5. Only records with:

       id <= cutoff_record_id

   are considered the historical offline backlog.
6. New telemetry generated after reconnection is excluded
   from the historical-backlog measurement.
7. Timing begins at T0, when the operator is instructed to
   restore network connectivity.
8. The experiment ends when BOTH frozen historical queues
   reach zero.

Metrics
-------
- Azure first backlog progress time
- ThingsBoard first backlog progress time
- Azure historical backlog recovery time
- ThingsBoard historical backlog recovery time
- Effective historical backfill throughput

Important
---------
This is NOT raw network throughput.

Recovery time includes the system-level path:
network restoration -> cloud reconnection -> synchronization
worker -> cloud upload -> SQLite status update.

Output
------
experiments/results/e3/e3_session_<N>.csv
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
        / "e3"
)


# ============================================================
# Experiment configuration
# ============================================================

DEFAULT_MIN_BACKLOG = 20

POLL_INTERVAL_SECONDS = 0.2

MAX_MONITOR_SECONDS = 180

DEFAULT_COUNTDOWN_SECONDS = 5


# ============================================================
# Utility functions
# ============================================================

def now_iso() -> str:
    """
    Return local timezone-aware ISO timestamp.
    """

    return (
        datetime.now()
        .astimezone()
        .isoformat()
    )


def get_database_state() -> dict:
    """
    Return current overall SQLite state.
    """

    with sqlite3.connect(
            DATABASE_PATH
    ) as connection:

        max_id = connection.execute(
            """
            SELECT MAX(id)
            FROM telemetry
            """
        ).fetchone()[0]

        azure_pending = connection.execute(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE azure_status = 'pending'
            """
        ).fetchone()[0]

        thingsboard_pending = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM telemetry
                WHERE thingsboard_status = 'pending'
                """
            ).fetchone()[0]
        )

    return {
        "max_id": (
            int(max_id)
            if max_id is not None
            else 0
        ),

        "azure_pending":
            int(azure_pending),

        "thingsboard_pending":
            int(thingsboard_pending),
    }


def get_historical_pending(
        cutoff_record_id: int,
) -> dict:
    """
    Count pending records that belong only to the frozen
    historical backlog.

    Any telemetry created after cutoff_record_id is excluded.
    """

    with sqlite3.connect(
            DATABASE_PATH
    ) as connection:

        azure_pending = connection.execute(
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

        thingsboard_pending = (
            connection.execute(
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
        )

    return {
        "azure_pending":
            int(azure_pending),

        "thingsboard_pending":
            int(thingsboard_pending),
    }


def save_result(
        result_path: Path,
        row: dict,
) -> None:
    """
    Save exactly one formal E3 session result.
    """

    result_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with result_path.open(
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

        writer.writerow(
            row
        )


# ============================================================
# Main experiment
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser()

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
        "--min-backlog",
        type=int,
        default=DEFAULT_MIN_BACKLOG,
        help=(
            "Minimum historical pending records "
            "required for BOTH Azure and ThingsBoard."
        ),
    )

    parser.add_argument(
        "--countdown",
        type=int,
        default=DEFAULT_COUNTDOWN_SECONDS,
        help=(
            "Preparation countdown while Raspberry Pi "
            "must remain offline."
        ),
    )

    args = parser.parse_args()

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path = (
            RESULT_DIR
            / f"e3_session_{args.session}.csv"
    )

    # --------------------------------------------------------
    # Protect formal result files
    # --------------------------------------------------------

    if result_path.exists():
        raise RuntimeError(
            f"\nFormal E3 result already exists:\n"
            f"{result_path}\n\n"
            "Rename or remove it manually before "
            "repeating the session."
        )

    # --------------------------------------------------------
    # Freeze historical backlog
    # --------------------------------------------------------

    initial_state = (
        get_database_state()
    )

    cutoff_record_id = (
        initial_state["max_id"]
    )

    historical_initial = (
        get_historical_pending(
            cutoff_record_id
        )
    )

    initial_azure = (
        historical_initial[
            "azure_pending"
        ]
    )

    initial_thingsboard = (
        historical_initial[
            "thingsboard_pending"
        ]
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    print("=" * 72)

    print(
        "E3 DUAL-CLOUD RECOVERY MONITOR V2"
    )

    print("=" * 72)

    print(
        f"Session                  : "
        f"{args.session}"
    )

    print(
        f"Cutoff Record ID         : "
        f"{cutoff_record_id}"
    )

    print(
        f"Initial Azure backlog    : "
        f"{initial_azure}"
    )

    print(
        f"Initial TB backlog       : "
        f"{initial_thingsboard}"
    )

    print(
        f"Required minimum backlog : "
        f"{args.min_backlog}"
    )

    print("=" * 72)

    # --------------------------------------------------------
    # Formal experiment protection rule
    # --------------------------------------------------------

    if (
            initial_azure
            < args.min_backlog
            or initial_thingsboard
            < args.min_backlog
    ):
        raise RuntimeError(
            "\nE3 experiment NOT started.\n\n"
            "Insufficient historical backlog.\n\n"
            f"Required:\n"
            f"Azure >= {args.min_backlog}\n"
            f"ThingsBoard >= {args.min_backlog}\n\n"
            f"Observed:\n"
            f"Azure = {initial_azure}\n"
            f"ThingsBoard = {initial_thingsboard}\n\n"
            "Keep Raspberry Pi offline and allow "
            "main.py to generate more pending telemetry."
        )

    print()

    print(
        "Historical backlog requirement: PASS"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Raspberry Pi MUST still be OFFLINE."
    )

    print(
        "Do NOT restore network during the countdown."
    )

    print()

    # --------------------------------------------------------
    # Preparation countdown
    # --------------------------------------------------------

    for remaining in range(
            args.countdown,
            0,
            -1,
    ):

        print(
            f"Network restore command "
            f"in {remaining}..."
        )

        time.sleep(
            1
        )

    # --------------------------------------------------------
    # T0
    #
    # Timer starts immediately before operator restores
    # network connectivity.
    # --------------------------------------------------------

    monitor_started_at = (
        now_iso()
    )

    start_time = (
        time.perf_counter()
    )

    print()

    print("=" * 72)

    print(
        "T0 — RESTORE RASPBERRY PI NETWORK NOW"
    )

    print("=" * 72)

    print(
        f"Recovery timer started at: "
        f"{monitor_started_at}"
    )

    print()

    print(
        "Do not stop main.py."
    )

    print(
        "Do not stop this monitor."
    )

    print(
        "Waiting for historical backlog recovery..."
    )

    print()

    # --------------------------------------------------------
    # Event variables
    # --------------------------------------------------------

    azure_first_decrease_time = None

    thingsboard_first_decrease_time = (
        None
    )

    azure_zero_time = None

    thingsboard_zero_time = None

    previous_azure = (
        initial_azure
    )

    previous_thingsboard = (
        initial_thingsboard
    )

    # --------------------------------------------------------
    # Historical backlog monitor
    # --------------------------------------------------------

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
            current[
                "azure_pending"
            ]
        )

        thingsboard_pending = (
            current[
                "thingsboard_pending"
            ]
        )

        # ----------------------------------------------------
        # Azure first progress
        # ----------------------------------------------------

        if (
                azure_first_decrease_time
                is None
                and azure_pending
                < initial_azure
        ):

            azure_first_decrease_time = (
                elapsed
            )

            print(
                f"[{elapsed:8.3f}s] "
                f"Azure first backlog decrease: "
                f"{initial_azure} -> "
                f"{azure_pending}"
            )

        # ----------------------------------------------------
        # ThingsBoard first progress
        # ----------------------------------------------------

        if (
                thingsboard_first_decrease_time
                is None
                and thingsboard_pending
                < initial_thingsboard
        ):

            thingsboard_first_decrease_time = (
                elapsed
            )

            print(
                f"[{elapsed:8.3f}s] "
                f"ThingsBoard first backlog "
                f"decrease: "
                f"{initial_thingsboard} -> "
                f"{thingsboard_pending}"
            )

        # ----------------------------------------------------
        # Queue change display
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
                thingsboard_pending
                != previous_thingsboard
        ):

            print(
                f"[{elapsed:8.3f}s] "
                f"ThingsBoard historical pending: "
                f"{thingsboard_pending}"
            )

            previous_thingsboard = (
                thingsboard_pending
            )

        # ----------------------------------------------------
        # Azure historical queue cleared
        # ----------------------------------------------------

        if (
                azure_zero_time is None
                and azure_pending == 0
        ):

            azure_zero_time = (
                elapsed
            )

            print()

            print(
                f"[{elapsed:8.3f}s] "
                "AZURE HISTORICAL BACKLOG CLEARED"
            )

        # ----------------------------------------------------
        # ThingsBoard historical queue cleared
        # ----------------------------------------------------

        if (
                thingsboard_zero_time is None
                and thingsboard_pending == 0
        ):

            thingsboard_zero_time = (
                elapsed
            )

            print()

            print(
                f"[{elapsed:8.3f}s] "
                "THINGSBOARD HISTORICAL "
                "BACKLOG CLEARED"
            )

        # ----------------------------------------------------
        # Experiment complete
        # ----------------------------------------------------

        if (
                azure_zero_time is not None
                and thingsboard_zero_time
                is not None
        ):
            break

        # ----------------------------------------------------
        # Timeout
        # ----------------------------------------------------

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

    # --------------------------------------------------------
    # Final timestamps
    # --------------------------------------------------------

    monitor_finished_at = (
        now_iso()
    )

    total_elapsed = (
            time.perf_counter()
            - start_time
    )

    # --------------------------------------------------------
    # Effective historical backfill throughput
    # --------------------------------------------------------

    azure_throughput = None

    if (
            azure_zero_time is not None
            and azure_zero_time > 0
    ):

        azure_throughput = (
                initial_azure
                / azure_zero_time
        )

    thingsboard_throughput = None

    if (
            thingsboard_zero_time
            is not None
            and thingsboard_zero_time > 0
    ):

        thingsboard_throughput = (
                initial_thingsboard
                / thingsboard_zero_time
        )

    # --------------------------------------------------------
    # Overall experiment result
    # --------------------------------------------------------

    success = (
            azure_zero_time is not None
            and thingsboard_zero_time
            is not None
    )

    # --------------------------------------------------------
    # Result row
    # --------------------------------------------------------

    result = {
        "session":
            args.session,

        "monitor_started_at":
            monitor_started_at,

        "monitor_finished_at":
            monitor_finished_at,

        "cutoff_record_id":
            cutoff_record_id,

        "minimum_required_backlog":
            args.min_backlog,

        "initial_azure_backlog":
            initial_azure,

        "initial_thingsboard_backlog":
            initial_thingsboard,

        "azure_first_decrease_time_s":
            (
                round(
                    azure_first_decrease_time,
                    3,
                )
                if azure_first_decrease_time
                   is not None
                else ""
            ),

        "thingsboard_first_decrease_time_s":
            (
                round(
                    thingsboard_first_decrease_time,
                    3,
                )
                if thingsboard_first_decrease_time
                   is not None
                else ""
            ),

        "azure_recovery_time_s":
            (
                round(
                    azure_zero_time,
                    3,
                )
                if azure_zero_time
                   is not None
                else ""
            ),

        "thingsboard_recovery_time_s":
            (
                round(
                    thingsboard_zero_time,
                    3,
                )
                if thingsboard_zero_time
                   is not None
                else ""
            ),

        "azure_effective_backfill_throughput_records_per_s":
            (
                round(
                    azure_throughput,
                    4,
                )
                if azure_throughput
                   is not None
                else ""
            ),

        "thingsboard_effective_backfill_throughput_records_per_s":
            (
                round(
                    thingsboard_throughput,
                    4,
                )
                if thingsboard_throughput
                   is not None
                else ""
            ),

        "monitor_duration_s":
            round(
                total_elapsed,
                3,
            ),

        "result":
            (
                "PASS"
                if success
                else "FAIL"
            ),
    }

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_result(
        result_path,
        result,
    )

    # --------------------------------------------------------
    # Console result
    # --------------------------------------------------------

    print()

    print("=" * 72)

    print(
        "E3 FORMAL RESULT"
    )

    print("=" * 72)

    print(
        f"Historical cutoff ID        : "
        f"{cutoff_record_id}"
    )

    print(
        f"Azure initial backlog       : "
        f"{initial_azure}"
    )

    print(
        f"ThingsBoard initial backlog : "
        f"{initial_thingsboard}"
    )

    print()

    if (
            azure_first_decrease_time
            is not None
    ):

        print(
            f"Azure first progress        : "
            f"{azure_first_decrease_time:.3f} s"
        )

    else:

        print(
            "Azure first progress        : FAILED"
        )

    if (
            thingsboard_first_decrease_time
            is not None
    ):

        print(
            f"ThingsBoard first progress  : "
            f"{thingsboard_first_decrease_time:.3f} s"
        )

    else:

        print(
            "ThingsBoard first progress  : FAILED"
        )

    print()

    if azure_zero_time is not None:

        print(
            f"Azure recovery time         : "
            f"{azure_zero_time:.3f} s"
        )

    else:

        print(
            "Azure recovery time         : FAILED"
        )

    if thingsboard_zero_time is not None:

        print(
            f"ThingsBoard recovery time   : "
            f"{thingsboard_zero_time:.3f} s"
        )

    else:

        print(
            "ThingsBoard recovery time   : FAILED"
        )

    print()

    if azure_throughput is not None:

        print(
            f"Azure effective throughput  : "
            f"{azure_throughput:.4f} records/s"
        )

    if thingsboard_throughput is not None:

        print(
            f"TB effective throughput     : "
            f"{thingsboard_throughput:.4f} records/s"
        )

    print()

    print(
        f"Overall result              : "
        f"{result['result']}"
    )

    print()

    print(
        f"Saved to:\n"
        f"{result_path}"
    )


if __name__ == "__main__":
    main()