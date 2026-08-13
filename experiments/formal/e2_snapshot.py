"""
E2 Experiment Snapshot Utility

Records SQLite and dual-cloud queue state at key
experiment stages.

Stages:
    pre
    offline_end
    recovered

This utility does NOT control hardware or networking.
It only observes experiment state.
"""

import argparse
import csv
import sqlite3
from datetime import datetime
from pathlib import Path


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
        / "e2"
)


def read_database_state() -> dict:
    with sqlite3.connect(
            DATABASE_PATH
    ) as connection:

        total = connection.execute(
            """
            SELECT COUNT(*)
            FROM telemetry
            """
        ).fetchone()[0]

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

        tb_pending = connection.execute(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE thingsboard_status = 'pending'
            """
        ).fetchone()[0]

    return {
        "total_records": int(total),
        "max_record_id": (
            int(max_id)
            if max_id is not None
            else 0
        ),
        "azure_pending": int(
            azure_pending
        ),
        "thingsboard_pending": int(
            tb_pending
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--session",
        type=int,
        required=True,
        choices=[1, 2, 3],
    )

    parser.add_argument(
        "--stage",
        required=True,
        choices=[
            "pre",
            "offline_end",
            "recovered",
        ],
    )

    args = parser.parse_args()

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path = (
            RESULT_DIR
            / f"e2_session_{args.session}_snapshots.csv"
    )

    state = read_database_state()

    timestamp = (
        datetime.now()
        .astimezone()
        .isoformat()
    )

    new_file = not result_path.exists()

    with result_path.open(
            "a",
            newline="",
            encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        if new_file:
            writer.writerow(
                [
                    "session",
                    "stage",
                    "timestamp",
                    "total_records",
                    "max_record_id",
                    "azure_pending",
                    "thingsboard_pending",
                ]
            )

        writer.writerow(
            [
                args.session,
                args.stage,
                timestamp,
                state["total_records"],
                state["max_record_id"],
                state["azure_pending"],
                state[
                    "thingsboard_pending"
                ],
            ]
        )

    print("=" * 65)
    print("E2 EXPERIMENT SNAPSHOT")
    print("=" * 65)

    print(
        f"Session             : "
        f"{args.session}"
    )

    print(
        f"Stage               : "
        f"{args.stage}"
    )

    print(
        f"Timestamp           : "
        f"{timestamp}"
    )

    print(
        f"Total records       : "
        f"{state['total_records']}"
    )

    print(
        f"Max Record ID       : "
        f"{state['max_record_id']}"
    )

    print(
        f"Azure pending       : "
        f"{state['azure_pending']}"
    )

    print(
        f"ThingsBoard pending : "
        f"{state['thingsboard_pending']}"
    )

    print("=" * 65)

    print(
        f"Saved to:\n"
        f"{result_path}"
    )


if __name__ == "__main__":
    main()