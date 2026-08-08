import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = (
        Path.home()
        / "azure-iot-environment"
        / "database"
        / "environment.db"
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteService:
    def __init__(self) -> None:
        if not DATABASE_PATH.exists():
            raise RuntimeError(
                f"Database not found: {DATABASE_PATH}"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        return connection

    def save_telemetry(
            self,
            payload: dict[str, Any],
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO telemetry (
                    device_id,
                    temperature,
                    humidity,
                    state,
                    led,
                    buzzer,
                    timestamp,
                    upload_status,
                    upload_attempts,
                    azure_status,
                    azure_attempts,
                    thingsboard_status,
                    thingsboard_attempts
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    'pending', 0,
                    'pending', 0,
                    'pending', 0
                )
                """,
                (
                    payload["deviceId"],
                    payload["temperature"],
                    payload["humidity"],
                    payload["state"],
                    int(payload["led"]),
                    int(payload["buzzer"]),
                    payload["timestamp"],
                ),
            )

            return int(cursor.lastrowid)

    def get_azure_pending(
            self,
            limit: int = 20,
    ) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT *
                FROM telemetry
                WHERE azure_status = 'pending'
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def get_thingsboard_pending(
            self,
            limit: int = 20,
    ) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT *
                FROM telemetry
                WHERE thingsboard_status = 'pending'
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def mark_azure_uploaded(
            self,
            record_id: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE telemetry
                SET
                    azure_status = 'uploaded',
                    azure_uploaded_at = ?,
                    azure_attempts = azure_attempts + 1
                WHERE id = ?
                """,
                (
                    utc_timestamp(),
                    record_id,
                ),
            )

    def mark_azure_failed(
            self,
            record_id: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE telemetry
                SET azure_attempts = azure_attempts + 1
                WHERE id = ?
                """,
                (record_id,),
            )

    def mark_thingsboard_uploaded(
            self,
            record_id: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE telemetry
                SET
                    thingsboard_status = 'uploaded',
                    thingsboard_uploaded_at = ?,
                    thingsboard_attempts =
                        thingsboard_attempts + 1
                WHERE id = ?
                """,
                (
                    utc_timestamp(),
                    record_id,
                ),
            )

    def mark_thingsboard_failed(
            self,
            record_id: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE telemetry
                SET thingsboard_attempts =
                    thingsboard_attempts + 1
                WHERE id = ?
                """,
                (record_id,),
            )

    def count_status(self) -> dict[str, int]:
        with self._connect() as connection:
            azure_pending = connection.execute(
                """
                SELECT COUNT(*)
                FROM telemetry
                WHERE azure_status = 'pending'
                """
            ).fetchone()[0]

            thingsboard_pending = connection.execute(
                """
                SELECT COUNT(*)
                FROM telemetry
                WHERE thingsboard_status = 'pending'
                """
            ).fetchone()[0]

            total = connection.execute(
                """
                SELECT COUNT(*)
                FROM telemetry
                """
            ).fetchone()[0]

        return {
            "total": int(total),
            "azurePending": int(azure_pending),
            "thingsboardPending": int(
                thingsboard_pending
            ),
        }