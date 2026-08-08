import sqlite3
from pathlib import Path


DATABASE_PATH = Path.home() / (
    "azure-iot-environment/database/environment.db"
)


def main() -> None:
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                state TEXT NOT NULL,
                led INTEGER NOT NULL,
                buzzer INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                upload_status TEXT NOT NULL DEFAULT 'pending',
                uploaded_at TEXT,
                upload_attempts INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_telemetry_upload_status
            ON telemetry(upload_status)
            """
        )

        connection.commit()

        print("=" * 58)
        print("SQLite database initialized successfully")
        print(f"Database: {DATABASE_PATH}")
        print("Table   : telemetry")
        print("=" * 58)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
