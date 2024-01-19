"""Utility classes for the Flex Thermostat integration."""
from __future__ import annotations
from homeassistant.backports.enum import StrEnum
from homeassistant.components.climate.const import HVACMode


class FanMode(StrEnum):
    """Fan Mode for Climate Devices."""

    OFF = "off"
    ON = "on"
    AUTO = "auto"


class UpdateResult:
    """Update result class."""

    is_handled: bool = False
    is_deferred: bool = False

    def __add__(self, other: UpdateResult) -> UpdateResult:
        """Add two UpdateResults together."""

        result: UpdateResult = UpdateResult()
        result.is_handled = self.is_handled or other.is_handled
        result.is_deferred = self.is_deferred or other.is_deferred

        return result


class ClimateSettings:
    """Class to store current and preset thermostat settings."""

    target_temperature_high: float | None
    target_temperature_low: float | None
    target_temperature: float | None
    hvac_mode: HVACMode
    fan_mode: FanMode

    def __init__(
        self,
        target_temperature_low: float | None,
        target_temperature_high: float | None,
        target_temperature: float | None,
        hvac_mode: HVACMode,
        fan_mode: FanMode | None,
    ) -> None:
        """Initialize an instance of the thermostat preset."""
        if (
            target_temperature is None
            and target_temperature_high is None
            and target_temperature_low is None
        ):
            raise RuntimeError("A target temperature or range must be specified")
        if (target_temperature_low is not None and target_temperature_high is None) or (
            target_temperature_low is None and target_temperature_high is not None
        ):
            raise RuntimeError(
                "When defining a temperature range both high and low values must be specified"
            )
        elif target_temperature is not None and (
            target_temperature_high is not None or target_temperature_low is not None
        ):
            raise RuntimeError(
                "When defining a temperature target only the target can be defined"
            )

        self.target_temperature_low = target_temperature_low
        self.target_temperature_high = target_temperature_high
        self.target_temperature = target_temperature
        self.hvac_mode = hvac_mode
        self.fan_mode = fan_mode

    def clone(self) -> ClimateSettings:
        """Create a clone of the settings."""
        return ClimateSettings(
            self.target_temperature_low,
            self.target_temperature_high,
            self.target_temperature,
            self.hvac_mode,
            self.fan_mode,
        )
