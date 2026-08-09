import threading

from services.cloud_sync_service import CloudSyncService


class BackgroundCloudSync:
    """
    后台双云同步Worker。

    Azure / ThingsBoard网络通信全部在此线程运行，
    不允许阻塞主边缘控制循环。
    """

    def __init__(
            self,
            sync_service: CloudSyncService,
            interval_seconds: float = 5.0,
    ) -> None:

        self.sync_service = sync_service
        self.interval_seconds = interval_seconds

        self._stop_event = threading.Event()

        self._thread = threading.Thread(
            target=self._run,
            name="cloud-sync-thread",
            daemon=True,
        )

    def start(self) -> None:

        if self._thread.is_alive():
            return

        print(
            "Background cloud sync: STARTED"
        )

        self._thread.start()

    def _run(self) -> None:

        while not self._stop_event.is_set():

            try:

                self.sync_service.sync_all()

            except Exception as error:

                print(
                    "\n[Cloud background error] "
                    f"{type(error).__name__}: "
                    f"{error}"
                )

            self._stop_event.wait(
                self.interval_seconds
            )

    def stop(self) -> None:

        print(
            "Background cloud sync: STOPPING"
        )

        self._stop_event.set()

        self._thread.join(
            timeout=3
        )

        if self._thread.is_alive():
            print(
                "Background cloud sync: "
                "still finishing network operation "
                "(daemon thread)"
            )
        else:
            print(
                "Background cloud sync: STOPPED"
            )