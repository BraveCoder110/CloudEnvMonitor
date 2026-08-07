import json
import threading
from pathlib import Path
from typing import Any


CONFIG_PATH = (
        Path.home()
        / "azure-iot-environment"
        / "config"
        / "settings.json"
)


DEFAULT_CONFIG = {
    "highTemperatureThreshold": 28.0,
    "autoMode": True,
    "buzzerEnabled": True,
    "fanEnabled": True,
}


class ConfigManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._config = DEFAULT_CONFIG.copy()

        self.load()

    def load(self) -> None:
        with self._lock:
            if not CONFIG_PATH.exists():
                self._save_unlocked()
                return

            try:
                with CONFIG_PATH.open(
                        "r",
                        encoding="utf-8",
                ) as file:
                    saved_config = json.load(file)

                self._config.update(saved_config)

            except (
                    json.JSONDecodeError,
                    OSError,
            ) as error:
                print(
                    "WARNING: Could not load settings.json:"
                    f" {error}"
                )

    def _save_unlocked(self) -> None:
        CONFIG_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with CONFIG_PATH.open(
                "w",
                encoding="utf-8",
        ) as file:
            json.dump(
                self._config,
                file,
                indent=2,
            )

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    def get(
            self,
            key: str,
            default: Any = None,
    ) -> Any:
        with self._lock:
            return self._config.get(
                key,
                default,
            )

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return self._config.copy()

    def update(
            self,
            updates: dict[str, Any],
    ) -> dict[str, Any]:
        accepted: dict[str, Any] = {}

        with self._lock:
            if "highTemperatureThreshold" in updates:
                value = updates[
                    "highTemperatureThreshold"
                ]

                try:
                    value = float(value)

                    if 10.0 <= value <= 50.0:
                        self._config[
                            "highTemperatureThreshold"
                        ] = value

                        accepted[
                            "highTemperatureThreshold"
                        ] = value

                    else:
                        print(
                            "Rejected highTemperatureThreshold: "
                            "must be between 10 and 50 °C"
                        )

                except (
                        TypeError,
                        ValueError,
                ):
                    print(
                        "Rejected highTemperatureThreshold: "
                        "not a valid number"
                    )

            for boolean_key in (
                    "autoMode",
                    "buzzerEnabled",
                    "fanEnabled",
            ):
                if boolean_key in updates:
                    value = updates[boolean_key]

                    if isinstance(value, bool):
                        self._config[
                            boolean_key
                        ] = value

                        accepted[
                            boolean_key
                        ] = value

                    else:
                        print(
                            f"Rejected {boolean_key}: "
                            "must be true or false"
                        )

            self._save_unlocked()

        return accepted