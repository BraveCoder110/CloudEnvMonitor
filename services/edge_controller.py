from enum import Enum


class SystemState(Enum):
    NORMAL = "NORMAL"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    SENSOR_ERROR = "SENSOR_ERROR"


class EdgeController:
    @staticmethod
    def determine_state(
            temperature: float | None,
            threshold: float,
    ) -> SystemState:
        if temperature is None:
            return SystemState.SENSOR_ERROR

        if temperature >= threshold:
            return SystemState.HIGH_TEMPERATURE

        return SystemState.NORMAL