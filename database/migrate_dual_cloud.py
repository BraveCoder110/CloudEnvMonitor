import sqlite3
from pathlib import Path


DATABASE_PATH = (
        Path.home()
        / "azure-iot-environment"
        / "database"
        / "environment.db"
)


def column_exists(
        connection: sqlite3.Connection,
        column_name: str,
) -> bool:
    rows = connection.execute(
        "PRAGMA table_info(telemetry)"
    ).fetchall()

    existing_columns = {
        row[1]
        for row in rows
    }

    return column_name in existing_columns


def add_column_if_missing(
        connection: sqlite3.Connection,
        column_name: str,
        definition: str,
) -> None:
    if column_exists(
            connection,
            column_name,
    ):
        print(
            f"Column already exists: "
            f"{column_name}"
        )
        return

    connection.execute(
        f"""
        ALTER TABLE telemetry
        ADD COLUMN {column_name} {definition}
        """
    )

    print(
        f"Added column: {column_name}"
    )


def main() -> None:
    print("=" * 65)
    print("Dual-Cloud Database Migration")
    print(f"Database: {DATABASE_PATH}")
    print("=" * 65)

    with sqlite3.connect(
            DATABASE_PATH
    ) as connection:

        add_column_if_missing(
            connection,
            "azure_status",
            "TEXT NOT NULL DEFAULT 'pending'",
        )

        add_column_if_missing(
            connection,
            "azure_uploaded_at",
            "TEXT",
        )

        add_column_if_missing(
            connection,
            "azure_attempts",
            "INTEGER NOT NULL DEFAULT 0",
        )

        add_column_if_missing(
            connection,
            "thingsboard_status",
            "TEXT NOT NULL DEFAULT 'pending'",
        )

        add_column_if_missing(
            connection,
            "thingsboard_uploaded_at",
            "TEXT",
        )

        add_column_if_missing(
            connection,
            "thingsboard_attempts",
            "INTEGER NOT NULL DEFAULT 0",
        )

        # Existing historical records were already uploaded
        # to Azure in the old system.
        connection.execute(
            """
            UPDATE telemetry
            SET
                azure_status = 'uploaded',
                azure_uploaded_at = uploaded_at,
                azure_attempts = upload_attempts
            WHERE upload_status = 'uploaded'
            """
        )

        # Old records were created before ThingsBoard
        # dual-cloud tracking existed.
        # We mark them legacy instead of incorrectly
        # pretending they were uploaded to ThingsBoard.
        connection.execute(
            """
            UPDATE telemetry
            SET thingsboard_status = 'legacy'
            WHERE upload_status = 'uploaded'
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_telemetry_azure_status
            ON telemetry(azure_status)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_telemetry_thingsboard_status
            ON telemetry(thingsboard_status)
            """
        )

        connection.commit()

    print("\nMigration completed successfully.")


if __name__ == "__main__":
    main()