"""The Flex Thermostat integration."""

from __future__ import annotations
from datetime import timedelta
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate import PLATFORM_SCHEMA
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature, ATTR_NAME
from homeassistant.components.climate.const import (
    ATTR_MIN_TEMP,
    ATTR_MAX_TEMP,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODES,
)

from .flex_thermostat import FlexThermostat
from .utilities import FanMode, ClimateSettings
from .const import (
    ATTR_TEMP_SENSOR,
    ATTR_HEATER_SWITCH,
    ATTR_COOLER_SWITCH,
    ATTR_FAN_SWITCH,
    ATTR_TEMP_TOLERANCE,
    ATTR_TEMP_STEP,
    ATTR_TARGET_TEMP,
    ATTR_DEFAULT_PRESET_HVAC_MODE,
    ATTR_DEFAULT_PRESET_FAN_MODE,
    ATTR_CLIMATE_CYCLE_RUNTIME,
    ATTR_CLIMATE_CYCLE_COOLDOWN,
    ATTR_INITIAL_PRESET,
    ATTR_INITIAL_SETTINGS,
    ATTR_OPENINGS,
    ATTR_OPENING_ENTITY,
    ATTR_OPENING_DELAY,
    ATTR_DEFAULT_OPENING_DELAY,
)

DEFAULT_TEMP_C_MIN = 7
DEFAULT_TEMP_C_MAX = 35
DEFAULT_TEMP_F_MIN = 40
DEFAULT_TEMP_F_MAX = 80
DEFAULT_TEMP_K_MIN = 280
DEFAULT_TEMP_K_MAX = 308
DEFAUL_CLIMATE_CYCLE_COOLDOWN = timedelta(minutes=5)
DEFAUL_CLIMATE_CYCLE_RUNTIME = None
DEFAULT_OPENING_DELAY = timedelta(seconds=30)
DEFAULT_TEMP_TOLERANCE = 0.75
DEFAULT_FAN_MODE = FanMode.OFF
DEFAULT_HVAC_MODE = HVACMode.OFF

CLIMATE_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_TARGET_TEMP): vol.Coerce(float),
        vol.Optional(ATTR_TARGET_TEMP_LOW): vol.Coerce(float),
        vol.Optional(ATTR_TARGET_TEMP_HIGH): vol.Coerce(float),
        vol.Optional(ATTR_FAN_MODE): vol.In([FanMode.ON, FanMode.OFF, FanMode.AUTO]),
        vol.Optional(ATTR_HVAC_MODE): vol.In(
            [
                HVACMode.COOL,
                HVACMode.HEAT,
                HVACMode.OFF,
                HVACMode.HEAT_COOL,
                HVACMode.FAN_ONLY,
            ]
        ),
    }
)

OPENING_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_OPENING_ENTITY): cv.entity_id,
        vol.Optional(ATTR_OPENING_DELAY): vol.All(cv.time_period, cv.positive_timedelta),
    }
)

PRESET_SCHEMA = CLIMATE_SETTINGS_SCHEMA.extend({vol.Required(ATTR_NAME): cv.string})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(ATTR_NAME): cv.string,
        # Entities
        vol.Required(ATTR_TEMP_SENSOR): cv.entity_id,
        vol.Optional(ATTR_COOLER_SWITCH): cv.entity_id,
        vol.Optional(ATTR_HEATER_SWITCH): cv.entity_id,
        vol.Optional(ATTR_FAN_SWITCH): cv.entity_id,
        # General Thermostat Settings
        vol.Optional(ATTR_MIN_TEMP): vol.Coerce(float),
        vol.Optional(ATTR_MAX_TEMP): vol.Coerce(float),
        vol.Optional(ATTR_TEMP_STEP): vol.Coerce(float),
        vol.Optional(ATTR_TEMP_TOLERANCE): vol.Coerce(float),
        # Presets/Openings
        vol.Optional(ATTR_PRESET_MODES): vol.All(cv.ensure_list, [PRESET_SCHEMA]),
        vol.Optional(ATTR_OPENINGS): vol.All(cv.ensure_list, [OPENING_SCHEMA]),
        # Configurable Defaults
        vol.Optional(ATTR_DEFAULT_OPENING_DELAY): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(ATTR_DEFAULT_PRESET_HVAC_MODE): vol.In(
            [
                HVACMode.COOL,
                HVACMode.HEAT,
                HVACMode.OFF,
                HVACMode.HEAT_COOL,
                HVACMode.FAN_ONLY,
            ]
        ),
        vol.Optional(ATTR_DEFAULT_PRESET_FAN_MODE): vol.In([FanMode.ON, FanMode.OFF, FanMode.AUTO]),
        # Initial Settings
        vol.Optional(ATTR_INITIAL_PRESET): cv.string,
        vol.Optional(ATTR_INITIAL_SETTINGS): CLIMATE_SETTINGS_SCHEMA,
    }
)

# Additional validations
PLATFORM_SCHEMA = vol.All(
    cv.has_at_least_one_key(ATTR_COOLER_SWITCH, ATTR_HEATER_SWITCH, ATTR_FAN_SWITCH),
    PLATFORM_SCHEMA,
)


def _proccess_climate_settings(
    settings_config: ConfigType,
    name: str,
    fallback_hvac_mode: HVACMode | None,
    fallback_fan_mode: FanMode | None,
) -> ClimateSettings:
    """Parse and validate ClimateSettings from a given config."""
    target_temperature = settings_config.get(ATTR_TARGET_TEMP)
    target_temperature_low = settings_config.get(ATTR_TARGET_TEMP_LOW)
    target_temperature_high = settings_config.get(ATTR_TARGET_TEMP_HIGH)
    hvac_mode = settings_config.get(ATTR_HVAC_MODE, fallback_hvac_mode)
    fan_mode = settings_config.get(ATTR_FAN_MODE, fallback_fan_mode)

    if hvac_mode is None:
        raise vol.Invalid(f"A HVACMode is required for {name}")
    elif hvac_mode != HVACMode.HEAT_COOL and (target_temperature_low is not None or target_temperature_high is not None):
        raise vol.Invalid(f"A target temperature range cannot be used for {name}")
    elif hvac_mode == HVACMode.HEAT_COOL and target_temperature_low is None:
        raise vol.Invalid(f"A lower bound for the target temperature range is required for {name}")
    elif hvac_mode == HVACMode.HEAT_COOL and target_temperature_high is None:
        raise vol.Invalid(f"An upper bound for the target temperature range is required for {name}")
    elif hvac_mode in [HVACMode.HEAT, HVACMode.COOL] and target_temperature is None:
        raise vol.Invalid(f"Target temperature required for {name}")

    return ClimateSettings(
        target_temperature_low,
        target_temperature_high,
        target_temperature,
        hvac_mode,
        fan_mode,
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    _: DiscoveryInfoType | None = None,
) -> None:
    """Initialize the Flex Thermostat Platform."""

    name: str = config[ATTR_NAME]
    temperature_sensor_id: str = config.get(ATTR_TEMP_SENSOR)
    heater_switch_id: str = config.get(ATTR_HEATER_SWITCH)
    cooler_switch_id: str = config.get(ATTR_COOLER_SWITCH)
    fan_switch_id: str = config.get(ATTR_FAN_SWITCH)
    climate_cycle_runtime: float | None = config.get(ATTR_CLIMATE_CYCLE_RUNTIME, DEFAUL_CLIMATE_CYCLE_RUNTIME)
    climate_cycle_cooldown: float | None = config.get(ATTR_CLIMATE_CYCLE_COOLDOWN, DEFAUL_CLIMATE_CYCLE_COOLDOWN)

    default_preset_hvac_mode = config.get(ATTR_DEFAULT_PRESET_HVAC_MODE, DEFAULT_HVAC_MODE)
    default_preset_fan_mode = config.get(ATTR_DEFAULT_PRESET_FAN_MODE, DEFAULT_FAN_MODE)
    default_opening_delay = config.get(ATTR_DEFAULT_OPENING_DELAY, DEFAULT_OPENING_DELAY)

    temperature_unit: UnitOfTemperature = hass.config.units.temperature_unit

    default_temperature_min: float
    default_temperature_max: float
    if temperature_unit == UnitOfTemperature.CELSIUS:
        default_temperature_min = DEFAULT_TEMP_C_MIN
        default_temperature_max = DEFAULT_TEMP_C_MAX
    elif temperature_unit == UnitOfTemperature.FAHRENHEIT:
        default_temperature_min = DEFAULT_TEMP_F_MIN
        default_temperature_max = DEFAULT_TEMP_F_MAX
    else:
        default_temperature_min = DEFAULT_TEMP_K_MIN
        default_temperature_max = DEFAULT_TEMP_K_MAX

    temperature_min: float = config.get(ATTR_MIN_TEMP, default_temperature_min)
    temperature_max: float = config.get(ATTR_MAX_TEMP, default_temperature_max)
    temperature_tolerance: float = config.get(ATTR_TEMP_TOLERANCE, DEFAULT_TEMP_TOLERANCE)
    temperature_step: float = config.get(ATTR_TEMP_STEP, 1.0)

    initial_preset: str | None = config.get(ATTR_INITIAL_PRESET, None)
    initial_settings: ClimateSettings | None = None
    if config[ATTR_INITIAL_SETTINGS] is not None:
        initial_settings = _proccess_climate_settings(config[ATTR_INITIAL_SETTINGS], ATTR_INITIAL_SETTINGS, None, None)

    presets: dict[str, ClimateSettings] = dict[str, ClimateSettings]()
    if config[ATTR_PRESET_MODES] is not None:
        for preset_config in config[ATTR_PRESET_MODES]:
            preset_name = preset_config.get(ATTR_NAME)
            presets[preset_name] = _proccess_climate_settings(
                preset_config,
                preset_name,
                default_preset_hvac_mode,
                default_preset_fan_mode,
            )

    default_opening_delay: timedelta = config.get(ATTR_OPENING_DELAY, DEFAULT_OPENING_DELAY)
    openings: list[tuple[str, timedelta | None]] = list[tuple[str, timedelta | None]]()
    if config[ATTR_OPENINGS] is not None:
        for opening_config in config[ATTR_OPENINGS]:
            opening_entity_id: str = opening_config.get(ATTR_OPENING_ENTITY)
            default_opening_delay: float = opening_config.get(ATTR_OPENING_DELAY, default_opening_delay)

            opening = (opening_entity_id, default_opening_delay)
            openings.append(opening)

    entities = [
        FlexThermostat(
            name,
            temperature_sensor_id,
            heater_switch_id,
            cooler_switch_id,
            fan_switch_id,
            climate_cycle_runtime,
            climate_cycle_cooldown,
            openings,
            default_opening_delay,
            presets,
            default_preset_hvac_mode,
            default_preset_fan_mode,
            temperature_min,
            temperature_max,
            temperature_tolerance,
            temperature_unit,
            temperature_step,
            initial_preset,
            initial_settings,
        )
    ]
    async_add_entities(entities, update_before_add=True)
