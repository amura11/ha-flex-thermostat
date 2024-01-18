"""Flex Thermostat Constants."""
from logging import Logger, getLogger
from homeassistant.backports.enum import StrEnum

_LOGGER: Logger = getLogger(__package__)

# Entity IDs
ATTR_TEMP_SENSOR = "temp_sensor"
ATTR_HEATER_SWITCH = "heater_switch"
ATTR_COOLER_SWITCH = "cooler_switch"
ATTR_FAN_SWITCH = "fan_switch"

# General Thermostat Settings
ATTR_TEMP_TOLERANCE = "temp_tolerance"
ATTR_TEMP_STEP = "temp_step"

# Climate Cycle Settings
ATTR_CLIMATE_CYCLE_RUNTIME = "climate_cycle_runtime"
ATTR_CLIMATE_CYCLE_COOLDOWN = "climate_cycle_cooldown"

# Initial Settings
ATTR_INITIAL_PRESET = "initial_preset"
ATTR_INITIAL_SETTINGS = "initial_settings"

# Preset Settings
ATTR_TARGET_TEMP = "target_temp"
ATTR_DEFAULT_PRESET_HVAC_MODE = "default_preset_hvac_mode"
ATTR_DEFAULT_PRESET_FAN_MODE = "default_preset_fan_mode"

# Opening Settings
ATTR_OPENINGS = "openings"
ATTR_OPENING_ENTITY = "opening"
ATTR_OPENING_DELAY = "delay"
ATTR_DEFAULT_OPENING_DELAY = "default_opening_delay"

# State Attribute names
ATTR_MANUAL_FAN_MODE = "manual_fan_mode"
ATTR_MANUAL_HVAC_MODE = "manual_hvac_mode"
ATTR_MANUAL_TEMP_LOW = "manual_temp_low"
ATTR_MANUAL_TEMP_HIGH = "manual_temp_high"
ATTR_LAST_CYCLE = "last_cycle"

ATTR_CLIMATE_CYCLE_LAST_STOP = "climate_cycle_last_stop"
ATTR_CLIMATE_CYCLE_LAST_START = "climate_cycle_last_start"
ATTR_MANUAL_FAN_MODE = "fan_mode"
ATTR_MANUAL_HVAC_MODE = "hvac_mode"
ATTR_MANUAL_TARGET_TEMPERATURE = "target_temperature"
ATTR_MANUAL_TARGET_TEMPERATURE_LOW = "target_temperature_low"
ATTR_MANUAL_TARGET_TEMPERATURE_HIGH = "target_temperature_high"


class FanAction(StrEnum):
    """Fan Actions for Climate Devices."""

    OFF = "off"
    ON = "on"
    IDLE = "idle"
