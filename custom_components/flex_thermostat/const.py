"""Flex Thermostat Constants."""
from logging import Logger, getLogger
from homeassistant.backports.enum import StrEnum

_LOGGER: Logger = getLogger(__package__)

# Basic Config
CONF_NAME = "name"
CONF_TEMP_SENSOR = "temp_sensor"
CONF_HEATER_SWITCH = "heater_switch"
CONF_COOLER_SWITCH = "cooler_switch"
CONF_FAN_SWITCH = "fan_switch"

# General Thermostat Settings
CONF_TEMP_MIN = "temp_min"
CONF_TEMP_MAX = "temp_max"
CONF_TEMP_STEP = "temp_step"
CONF_TEMP_TOLERANCE = "temp_tolerance"
CONF_CLIMATE_CYCLE_RUNTIME = "climate_cycle_runtime"
CONF_CLIMATE_CYCLE_COOLDOWN = "climate_cycle_cooldown"

# Preset/ and Climate Settings
CONF_PRESETS = "presets"
CONF_PRESET_NAME = "name"
CONF_CLIMATE_TARGET_TEMP = "target_temp"
CONF_CLIMATE_TARGET_TEMP_LOW = "target_temp_low"
CONF_CLIMATE_TARGET_TEMP_HIGH = "target_temp_high"
CONF_CLIMATE_FAN_MODE = "fan_mode"
CONF_CLIMATE_HVAC_MODE = "hvac_mode"

# Opening Settings
CONF_OPENINGS = "openings"
CONF_OPENING_ENTITY = "opening"
CONF_OPENING_DELAY = "delay"
CONF_DEFAULT_OPENING_DELAY = "default_opening_delay"

# Configurable Defaults
CONF_DEFAULT_OPENING_DELAY = "default_opening_delay"
CONF_DEFAULT_PRESET_HVAC_MODE = "default_preset_hvac_mode"
CONF_DEFAULT_PRESET_FAN_MODE = "default_preset_fan_mode"

# Initial Settings
CONF_INITIAL_PRESET = "initial_preset"
CONF_INITIAL_SETTINGS = "initial_settings"

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
