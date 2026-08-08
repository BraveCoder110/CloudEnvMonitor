from cloud.azure_service import AzureService
from cloud.thingsboard_service import (
    ThingsBoardService,
)
from database.sqlite_service import SQLiteService


class CloudSyncService:
    def __init__(
            self,
            database: SQLiteService,
            azure: AzureService,
            thingsboard: ThingsBoardService,
    ) -> None:
        self.database = database
        self.azure = azure
        self.thingsboard = thingsboard

    @staticmethod
    def row_to_payload(
            row,
    ) -> dict:
        return {
            "recordId": row["id"],
            "deviceId": row["device_id"],
            "temperature": row["temperature"],
            "humidity": row["humidity"],
            "state": row["state"],
            "led": bool(row["led"]),
            "buzzer": bool(row["buzzer"]),
            "timestamp": row["timestamp"],
        }

    def sync_azure(
            self,
            limit: int = 20,
    ) -> tuple[int, int]:
        rows = self.database.get_azure_pending(
            limit
        )

        if not rows:
            print(
                "Azure queue: empty"
            )
            return 0, 0

        print(
            f"Azure queue: "
            f"{len(rows)} pending record(s)"
        )

        success_count = 0
        failure_count = 0

        for row in rows:
            record_id = int(
                row["id"]
            )

            payload = self.row_to_payload(
                row
            )

            success = (
                self.azure.send_telemetry(
                    payload
                )
            )

            if success:
                self.database.mark_azure_uploaded(
                    record_id
                )

                success_count += 1

                print(
                    f"  Azure Record "
                    f"{record_id}: SUCCESS"
                )

            else:
                self.database.mark_azure_failed(
                    record_id
                )

                failure_count += 1

                print(
                    f"  Azure Record "
                    f"{record_id}: FAILED"
                )

                # 网络异常后暂时停止本轮
                break

        return (
            success_count,
            failure_count,
        )

    def sync_thingsboard(
            self,
            limit: int = 20,
    ) -> tuple[int, int]:
        rows = (
            self.database
            .get_thingsboard_pending(
                limit
            )
        )

        if not rows:
            print(
                "ThingsBoard queue: empty"
            )
            return 0, 0

        print(
            f"ThingsBoard queue: "
            f"{len(rows)} pending record(s)"
        )

        success_count = 0
        failure_count = 0

        for row in rows:
            record_id = int(
                row["id"]
            )

            payload = self.row_to_payload(
                row
            )

            success = (
                self.thingsboard
                .send_telemetry(
                    payload
                )
            )

            if success:
                (
                    self.database
                    .mark_thingsboard_uploaded(
                        record_id
                    )
                )

                success_count += 1

                print(
                    f"  ThingsBoard Record "
                    f"{record_id}: SUCCESS"
                )

            else:
                (
                    self.database
                    .mark_thingsboard_failed(
                        record_id
                    )
                )

                failure_count += 1

                print(
                    f"  ThingsBoard Record "
                    f"{record_id}: FAILED"
                )

                break

        return (
            success_count,
            failure_count,
        )

    def sync_all(
            self,
    ) -> None:
        print(
            "\n--- Dual-cloud sync ---"
        )

        azure_success, azure_failed = (
            self.sync_azure()
        )

        tb_success, tb_failed = (
            self.sync_thingsboard()
        )

        status = (
            self.database.count_status()
        )

        print(
            "Sync result:"
        )

        print(
            f"Azure      : "
            f"success={azure_success}, "
            f"failed={azure_failed}"
        )

        print(
            f"ThingsBoard: "
            f"success={tb_success}, "
            f"failed={tb_failed}"
        )

        print(
            f"Database   : "
            f"total={status['total']}, "
            f"azurePending="
            f"{status['azurePending']}, "
            f"thingsboardPending="
            f"{status['thingsboardPending']}"
        )