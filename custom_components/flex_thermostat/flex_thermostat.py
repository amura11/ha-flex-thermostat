"""Thermostat implementation of the Flex Thermostat integration."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import asyncio
from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.restore_state import RestoreEntity

from homeassistant.const import (
    UnitOfTemperature,
    EVENT_HOMEASSISTANT_START,
    ATTR_TEMPERATURE,
)
from homeassistant.core import (
    State,
    Event,
    CoreState,
    callback,
    CALLBACK_TYPE,
)
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_point_in_utc_time,
)

from .switch_manager import SwitchManager
from .cycle_manager import CycleManager
from .opening_manager import OpeningManager
from .utilities import FanMode, ClimateSettings, UpdateResult
from .const import (
    _LOGGER,
    ATTR_CLIMATE_CYCLE_LAST_STOP,
    ATTR_CLIMATE_CYCLE_LAST_START,
    ATTR_MANUAL_FAN_MODE,
    ATTR_MANUAL_HVAC_MODE,
    ATTR_MANUAL_TARGET_TEMPERATURE,
    ATTR_MANUAL_TARGET_TEMPERATURE_LOW,
    ATTR_MANUAL_TARGET_TEMPERATURE_HIGH,
)


class FlexThermostat(ClimateEntity, RestoreEntity):
    """Flex Thermostat class that implements the core of the integration."""

    # General Settings
    _name: str
    _temperature_sensor_id: str
    _temperature_min: float
    _temperature_max: float
    _temperature_tolerance: float
    _temperature_unit: UnitOfTemperature
    _temperature_step: float
    _presets: dict[str, ClimateSettings]
    _default_hvac_mode: HVACMode
    _default_fan_mode: FanMode

    # Current States
    _current_temperature: float | None = None
    _current_settings: ClimateSettings
    _current_action: HVACAction
    _current_preset: str | None = None
    _previous_preset: str | None = None
    _previous_settings: ClimateSettings | None = None

    # Internal objects
    _heater_switch: SwitchManager
    _cooler_switch: SwitchManager
    _fan_switch: SwitchManager
    _climate_cycle_manager: CycleManager
    _opening_manager: OpeningManager
    _remove_pending_defferal_listener: CALLBACK_TYPE | None = None

    _base_supported_features: ClimateEntityFeature = ClimateEntityFeature(0)
    _available_hvac_modes: list[HVACMode] = [HVACMode.OFF]
    _available_fan_modes: list[FanMode] = []
    _is_initialized: bool = False

    def __init__(
        self,
        name: str,
        # Switches/Sensors
        temperature_sensor_id: str,
        heater_switch_id: str | None,
        cooler_switch_id: str | None,
        fan_switch_id: str | None,
        # Cycle Settings
        climate_cycle_runtime: timedelta | None,
        climate_cycle_cooldown: timedelta | None,
        # Opening settings
        opening_configs: list[tuple[str, timedelta | None]] | None,
        default_opening_delay: timedelta,
        # Preset Settings
        presets: dict[str, ClimateSettings],
        default_preset_hvac_mode: HVACMode,
        default_preset_fan_mode: FanMode,
        # General Settings
        temperature_min: float,
        temperature_max: float,
        temperature_tolerance: float,
        temperature_unit: UnitOfTemperature,
        temperature_step: float,
        # Initial Settings
        initial_preset: str | None,
        initial_settings: ClimateSettings | None,
    ) -> None:
        """Initialize a new instance of the FlexThermostat class."""

        super().__init__()

        # Initial defaults
        self._current_settings = ClimateSettings(None, None, 23, HVACMode.OFF, None)
        self._current_action = HVACAction.IDLE

        # General Settings
        self._name = name
        self._temperature_sensor_id = temperature_sensor_id
        self._temperature_min = temperature_min
        self._temperature_max = temperature_max
        self._temperature_tolerance = temperature_tolerance
        self._temperature_unit = temperature_unit
        self._temperature_step = temperature_step

        # Preset Settings
        self._presets = presets
        self._default_hvac_mode = default_preset_hvac_mode
        self._default_fan_mode = default_preset_fan_mode

        # Manager setup
        self._climate_cycle_manager = CycleManager(climate_cycle_runtime, climate_cycle_cooldown)
        self._heater_switch = SwitchManager(heater_switch_id)
        self._cooler_switch = SwitchManager(cooler_switch_id)
        self._fan_switch = SwitchManager(fan_switch_id)
        self._opening_manager = OpeningManager(opening_configs, default_opening_delay)

        # Mode/Features setup
        if fan_switch_id is not None:
            self._available_hvac_modes.append(HVACMode.FAN_ONLY)
            self._available_fan_modes = [FanMode.OFF, FanMode.ON, FanMode.AUTO]
            self._base_supported_features |= ClimateEntityFeature.FAN_MODE
        if heater_switch_id is not None:
            self._available_hvac_modes.append(HVACMode.HEAT)
        if cooler_switch_id is not None:
            self._available_hvac_modes.append(HVACMode.COOL)
        if heater_switch_id is not None and cooler_switch_id is not None:
            self._available_hvac_modes.append(HVACMode.HEAT_COOL)

        # Set defaults
        if (len(self._presets) > 0) and initial_preset is not None:
            self._current_preset = initial_preset
            self._current_settings = self._presets[initial_preset].clone()
        elif initial_settings is not None:
            self._current_settings = initial_settings

    # region Public Getters

    @property
    def name(self) -> str:
        """Returns the name of the entity."""
        return self._name

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation if supported."""
        return self._current_action

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self._current_preset

    @property
    def preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes."""
        return list(self._presets.keys())

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode."""
        return self._current_settings.hvac_mode

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available hvac operation modes."""
        return self._available_hvac_modes

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._current_settings.target_temperature

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        return self._current_settings.target_temperature_high

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        return self._current_settings.target_temperature_low

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return self._current_settings.fan_mode

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        return self._available_fan_modes

    @property
    def temperature_unit(self) -> UnitOfTemperature:
        """Gets the current temperature unit."""
        return self._temperature_unit

    @property
    def target_temperature_step(self) -> float | None:
        """Return the supported step of target temperature."""
        return self._temperature_step

    @property
    def min_temp(self) -> float:
        """Gets the minimum temperature."""
        return self._temperature_min

    @property
    def max_temp(self) -> float:
        """Gets the maximum temperature."""
        return self._temperature_max

    @property
    def should_poll(self) -> None:
        """Return whether the integration should poll."""
        return False

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return (
            self._base_supported_features | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            if self._is_dual_temperature_mode is True
            else self._base_supported_features | ClimateEntityFeature.TARGET_TEMPERATURE
        )

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes to be saved."""
        data: dict[str, any] = dict[str, any]()

        data[ATTR_CLIMATE_CYCLE_LAST_STOP] = (
            self._climate_cycle_manager.last_stop.isoformat() if self._climate_cycle_manager.last_stop is not None else None
        )
        data[ATTR_CLIMATE_CYCLE_LAST_START] = (
            self._climate_cycle_manager.last_start.isoformat() if self._climate_cycle_manager.last_start is not None else None
        )

        # If the climate settings are manual store them
        if self._current_preset is None:
            data[ATTR_MANUAL_HVAC_MODE] = self._current_settings.hvac_mode
            data[ATTR_MANUAL_FAN_MODE] = self._current_settings.fan_mode
            data[ATTR_MANUAL_TARGET_TEMPERATURE] = self._current_settings.target_temperature
            data[ATTR_MANUAL_TARGET_TEMPERATURE_LOW] = self._current_settings.target_temperature_low
            data[ATTR_MANUAL_TARGET_TEMPERATURE_HIGH] = self._current_settings.target_temperature_high

        return data

    # endregion

    # region Public Setters

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the new temperature."""
        target_temperature = kwargs.get(ATTR_TEMPERATURE)
        target_temperature_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        target_temperature_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        if self._is_dual_temperature_mode is False and target_temperature is None:
            raise ValueError("Target temperature required in current mode")
        elif self._is_dual_temperature_mode is True and target_temperature_low is None and target_temperature_high is None:
            raise ValueError("At least one temperature value is required")

        self._current_preset = None
        self._current_settings.target_temperature = (
            target_temperature if target_temperature is not None else self._current_settings.target_temperature
        )
        self._current_settings.target_temperature_low = (
            target_temperature_low if target_temperature_low is not None else self._current_settings.target_temperature_low
        )
        self._current_settings.target_temperature_high = (
            target_temperature_high if target_temperature_high is not None else self._current_settings.target_temperature_high
        )

        _LOGGER.debug(
            "Temperate range changed to %s - %s",
            target_temperature_low,
            target_temperature_high,
        )

        if self._is_initialized is True:
            await self._async_update()
        else:
            _LOGGER.debug("Temperature target changed but integration hasn't been initialized")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new hvac mode."""
        _LOGGER.debug("Setting HVac Mode to %s", hvac_mode)

        self._current_preset = None
        self._current_settings.hvac_mode = hvac_mode

        if self._is_initialized is True:
            await self._async_update()
        else:
            _LOGGER.debug("HVACMode changed but integration hasn't been initialized")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in self._presets:
            raise KeyError("Preset does not exist")

        _LOGGER.debug("Changing preset to %s", preset_mode)

        self._current_preset = preset_mode
        self._current_settings = self._presets[preset_mode].clone()

        if self._is_initialized is True:
            await self._async_update()
        else:
            _LOGGER.debug("Preset mode changed but integration hasn't been initialized")

    async def async_set_fan_mode(self, fan_mode: str | FanMode) -> None:
        """Set the the new fan mode."""
        _LOGGER.debug("Changing Fan Mode to %s", fan_mode)

        self._current_preset = None
        self._current_settings.fan_mode = fan_mode

        if self._is_initialized is True:
            await self._async_update()
        else:
            _LOGGER.debug("Preset mode changed but integration hasn't been initialized")

    # endregion

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""

        await super().async_added_to_hass()

        last_climate_cycle_stop: datetime | None = None
        last_climate_cycle_start: datetime | None = None

        # Load the previous state if it's present
        previous_state: State | None = await self.async_get_last_state()
        if previous_state is not None:
            _LOGGER.debug("Previous state found, loading data")
            # Get the previous climate cycle data
            if previous_state.attributes.get(ATTR_CLIMATE_CYCLE_LAST_START) is not None:
                last_climate_cycle_start = datetime.fromisoformat(previous_state.attributes.get(ATTR_CLIMATE_CYCLE_LAST_START))
                _LOGGER.debug("Loaded last climate cycle start as %s", last_climate_cycle_start)
            if previous_state.attributes.get(ATTR_CLIMATE_CYCLE_LAST_STOP) is not None:
                last_climate_cycle_stop = datetime.fromisoformat(previous_state.attributes.get(ATTR_CLIMATE_CYCLE_LAST_STOP))
                _LOGGER.debug("Loaded last climate cycle stop as %s", last_climate_cycle_stop)

            # Set the previous preset
            if (
                previous_preset := previous_state.attributes.get(ATTR_PRESET_MODE)
            ) is not None and previous_preset in self._presets:
                _LOGGER.debug("Previous state had preset %s", previous_preset)
                self._current_preset = previous_preset
                self._current_settings = self._presets[previous_preset].clone()
            elif (previous_settings := self._read_manual_settings(previous_state)) is not None:
                _LOGGER.debug("Previous state had manual settings %s", previous_settings)
                self._current_preset = None
                self._current_settings = previous_settings
            # Otherwise something is weird or we have no state so use the default

        # Setup listeners
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._temperature_sensor_id],
                self._async_on_temperature_changed,
            )
        )

        self.async_on_remove(self._cleanup)

        # Startup function to run at HA startup or on creation, loads current values and old state
        @callback
        def _async_startup(*_) -> None:
            sensor_state = self.hass.states.get(self._temperature_sensor_id)
            self._current_temperature = float(sensor_state.state) if sensor_state is not None else None

            self._heater_switch.initialize(self.hass, self._on_switch_changed)
            self._cooler_switch.initialize(self.hass, self._on_switch_changed)
            self._fan_switch.initialize(self.hass, self._on_switch_changed)
            self._opening_manager.initialize(self.hass, self._async_on_openings_state_changed)
            self._climate_cycle_manager.initialize(last_climate_cycle_start, last_climate_cycle_stop)

            self._is_initialized = True

            # Call update to get things going
            asyncio.run_coroutine_threadsafe(self._async_update(), self.hass.loop)

        # Call the startup function immediately if HA is running or wait until it is to run it
        if self.hass.state == CoreState.running:
            _async_startup()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

    def _on_switch_changed(self, _: Event):
        self._defer_update(timedelta(seconds=30))

    async def _async_on_openings_state_changed(self, _: bool) -> None:
        await self._async_update()

    async def _async_on_temperature_changed(self, event: Event):
        _LOGGER.debug("Temperature sensor updated")

        new_state = event.data.get("new_state")
        self._current_temperature = float(new_state.state)

        if self._is_initialized is True:
            await self._async_update()
        else:
            _LOGGER.debug("Temperature changed but integration hasn't been initialized")

    @property
    def _is_dual_temperature_mode(self) -> bool:
        # FUTURE: Add a flag that will use single temperature mode even when set to Heat/Cool
        return self._current_settings.hvac_mode == HVACMode.HEAT_COOL

    @property
    def _is_heating_required(self) -> bool:
        # Determine what target should be used
        target: float = (
            self._current_settings.target_temperature_low
            if self._is_dual_temperature_mode is True
            else self._current_settings.target_temperature
        )

        return (
            # Check if the current mode supports heating (may not be needed?)
            self._current_settings.hvac_mode in [HVACMode.HEAT, HVACMode.HEAT_COOL]
            # Check that no openings are open
            and self._opening_manager.is_any_opening_open is False
            # Check if the temperature is below the target
            and self._current_temperature - self._temperature_tolerance <= target
        )

    @property
    def _is_cooling_required(self) -> bool:
        # Determine what target should be used
        target: float = (
            self._current_settings.target_temperature_high
            if self._is_dual_temperature_mode is True
            else self._current_settings.target_temperature
        )

        return (
            # Check if the current mode supports heating (may not be needed?)
            self._current_settings.hvac_mode in [HVACMode.COOL, HVACMode.HEAT_COOL]
            # Check that no openings are open
            and self._opening_manager.is_any_opening_open is False
            # Check if the temperature is below the target
            and self._current_temperature + self._temperature_tolerance >= target
        )

    async def _async_update(self) -> None:
        requested_action: HVACAction
        current_hvac_mode: HVACMode = self._current_settings.hvac_mode

        # Determine what the new action should be
        # NOTE: There is some redundant sections, this is done for readability
        if current_hvac_mode == HVACMode.OFF:
            requested_action = HVACAction.OFF
        # Fan only mode
        elif current_hvac_mode == HVACMode.FAN_ONLY:
            requested_action = HVACAction.FAN
        # Heating only mode
        elif current_hvac_mode == HVACMode.HEAT:
            if self._is_heating_required is True:
                requested_action = HVACAction.HEATING
            else:
                requested_action = HVACAction.IDLE
        # Cooling only mode
        elif current_hvac_mode == HVACMode.COOL:
            if self._is_cooling_required is True:
                requested_action = HVACAction.COOLING
            else:
                requested_action = HVACAction.IDLE
        # Dual Mode
        elif current_hvac_mode == HVACMode.HEAT_COOL:
            if self._is_heating_required is True:
                requested_action = HVACAction.HEATING
            elif self._is_cooling_required is True:
                requested_action = HVACAction.COOLING
            else:
                requested_action = HVACAction.IDLE
        else:
            requested_action = HVACAction.IDLE

        # Determine what to do with the new action
        if requested_action != self._current_action:
            _LOGGER.debug(
                "Current action (%s) differs from requested action (%s), determining action",
                self._current_action,
                requested_action,
            )
            result: UpdateResult = UpdateResult()

            # Handle the action for heating/cooling
            if result.is_deferred is False:
                result += await self._async_handle_action_climate(requested_action)

            # Handle the action for the fan
            if result.is_deferred is False:
                result += await self._async_handle_action_fan(requested_action)

            if result.is_handled is True and result.is_deferred is True:
                raise RuntimeError("Action has both handled and deffered")
            elif result.is_deferred is True and requested_action == HVACAction.OFF:
                raise RuntimeError("Off action cannot be deferred")

            _LOGGER.debug("Handle action result: Deferred = %s | Handled = %s", result.is_deferred, result.is_handled)

            if result.is_handled is True or requested_action == HVACAction.OFF:
                self._current_action = requested_action

        else:
            _LOGGER.debug(
                "Current action and requested action are both (%s), taking no action.",
                self._current_action,
            )

        self.async_write_ha_state()

    async def _async_handle_action_fan(self, requested_action: HVACAction) -> UpdateResult:
        # Currently fan control doesn't support deferral so the is_deferred flag should remain false
        result: UpdateResult = UpdateResult()

        if self._fan_switch.is_enabled is True:
            if requested_action == HVACAction.OFF and self._fan_switch.is_active is True:
                _LOGGER.debug("Fan is not needed, turning off %s", self._fan_switch.entity_id)
                await self._fan_switch.async_turn_off()
            elif requested_action == HVACAction.FAN:
                if self._fan_switch.is_active is False:
                    _LOGGER.debug("Fan is needed, turning on %s", self._fan_switch.entity_id)
                    await self._fan_switch.async_turn_on()
                result.is_handled = True
            elif self._current_settings.fan_mode == FanMode.ON and self._fan_switch.is_active is False:
                _LOGGER.debug("Fan is needed, turning on %s", self._fan_switch.entity_id)
                await self._fan_switch.async_turn_on()
            elif self._current_settings.fan_mode == FanMode.OFF and self._fan_switch.is_active is True:
                _LOGGER.debug("Fan is not needed, turning off %s", self._fan_switch.entity_id)
                await self._fan_switch.async_turn_off()
            elif self._current_settings.fan_mode == FanMode.AUTO:
                if requested_action == HVACAction.HEATING or requested_action == HVACAction.COOLING:
                    if self._fan_switch.is_active is False:
                        _LOGGER.debug("Fan is needed, turning on %s", self._fan_switch.entity_id)
                        await self._fan_switch.async_turn_on()
                else:
                    if self._fan_switch.is_active is True:
                        _LOGGER.debug(
                            "Fan is not needed, turning off %s",
                            self._fan_switch.entity_id,
                        )
                        await self._fan_switch.async_turn_off()

        return result

    async def _async_handle_action_climate(self, requested_action: HVACAction) -> UpdateResult:
        result: UpdateResult = UpdateResult()

        # Heating scenario, will either handle or defer
        if requested_action == HVACAction.HEATING:
            _LOGGER.debug("Handling request for heating action for climate system")

            if self._cooler_switch.is_active is True:
                # Cooler is on and should be shut off
                if self._climate_cycle_manager.can_stop is True:
                    _LOGGER.debug(
                        "Heating requested while cooler is on, turning off %s",
                        self._cooler_switch.entity_id,
                    )
                    await self._cooler_switch.async_turn_off()
                    self._climate_cycle_manager.cycle_ended()
                else:
                    _LOGGER.debug("Heating requested while cooler in on but can't be stopped, deferring")
                    self._defer_update(self._climate_cycle_manager.remaining_stop_time)
                    result.is_deferred = True

            if self._heater_switch.is_active is False:
                # Heater is off and should be turned on
                if self._climate_cycle_manager.can_start is True:
                    _LOGGER.debug(
                        "Heating requested, turning on %s",
                        self._heater_switch.entity_id,
                    )
                    await self._heater_switch.async_turn_on()
                    self._climate_cycle_manager.cycle_started()
                    result.is_handled = True
                else:
                    _LOGGER.debug("Heating requested but can't be stopped, deferring")
                    self._defer_update(self._climate_cycle_manager.remaining_start_time)
                    result.is_deferred = True
            else:
                _LOGGER.warning("Heating requested and is already on, this is unexpected")
                self._climate_cycle_manager.cycle_started()
                result.is_handled = True

        # Cooling scenario, will either handle or defer
        elif requested_action == HVACAction.COOLING:
            if self._heater_switch.is_active is True:
                # Heater is on and should be shut off
                if self._climate_cycle_manager.can_stop is True:
                    _LOGGER.debug(
                        "Cooling requested while heater is on, turning off %s",
                        self._heater_switch.entity_id,
                    )
                    await self._heater_switch.async_turn_off()
                    self._climate_cycle_manager.cycle_ended()
                else:
                    _LOGGER.debug("Cooling requested while haeter in on but can't be stopped, deferring")
                    self._defer_update(self._climate_cycle_manager.remaining_stop_time)
                    result.is_deferred = True

            if self._cooler_switch.is_active is False:
                # Cooler is off and should be turned on
                if self._climate_cycle_manager.can_start is True:
                    _LOGGER.debug(
                        "Cooling requested, turning on %s",
                        self._cooler_switch.entity_id,
                    )
                    await self._cooler_switch.async_turn_on()
                    self._climate_cycle_manager.cycle_started()
                    result.is_handled = True
                else:
                    _LOGGER.debug("Cooling requested but can't be stopped, deferring")
                    self._defer_update(self._climate_cycle_manager.remaining_start_time)
                    result.is_deferred = True
            else:
                _LOGGER.warning("Cooling requested and is already on, this is unexpected")
                self._climate_cycle_manager.cycle_started()
                result.is_handled = True

        # Special scenario, turn off without checking if we can, will either handle quietly or defer
        elif requested_action == HVACAction.OFF:
            if self._heater_switch.is_active is True or self._cooler_switch.is_active is True:
                if self._heater_switch.is_active is True:
                    _LOGGER.debug(
                        "Off requested while heater is on, turning off %s",
                        self._heater_switch.entity_id,
                    )
                    await self._heater_switch.async_turn_off()

                if self._cooler_switch.is_active is True:
                    _LOGGER.debug(
                        "Off requested while cooler is on, turning off %s",
                        self._cooler_switch.entity_id,
                    )
                    await self._cooler_switch.async_turn_off()

                self._climate_cycle_manager.cycle_ended()

        # Other cases, idle or not heat/cool, will either handle quietly or defer
        else:
            if self._heater_switch.is_active is True or self._cooler_switch.is_active is True:
                if self._climate_cycle_manager.can_stop is True:
                    if self._heater_switch.is_active is True:
                        _LOGGER.debug(
                            "Heater is on but not needed, turning off %s",
                            self._heater_switch.entity_id,
                        )
                        await self._heater_switch.async_turn_off()

                    if self._cooler_switch.is_active is True:
                        _LOGGER.debug(
                            "Cooler is on but not needed, turning off %s",
                            self._cooler_switch.entity_id,
                        )
                        await self._cooler_switch.async_turn_off()

                    self._climate_cycle_manager.cycle_ended()
                    result.is_handled = True  # This may need to be set only when going from an active state to idle
                else:
                    _LOGGER.debug("Cooling requested while heater is on but can't be stopped, deferring")
                    self._defer_update(self._climate_cycle_manager.remaining_stop_time)
                    result.is_deferred = True

        return result

    def _defer_update(self, duration: timedelta) -> None:
        if duration.total_seconds() < 1:
            _LOGGER.debug(
                "Requested duration was < 1 second (%s), defaulting to 1 second",
                duration.total_seconds(),
            )
            duration = timedelta(seconds=1)

        if self._remove_pending_defferal_listener is None:
            _LOGGER.debug("Deferring update for %s second(s)", duration.total_seconds())
            point_in_time: datetime = datetime.now(timezone.utc) + duration
            self._remove_pending_defferal_listener = async_track_point_in_utc_time(
                self.hass, self._async_deferred_update, point_in_time
            )
        else:
            _LOGGER.debug("Deferral requested but one is pending, taking no action")

    async def _async_deferred_update(self, _: datetime):
        await self._async_update()

    def _cleanup(self) -> None:
        # Cleanup any pending deferrals
        if self._remove_pending_defferal_listener is not None:
            self._remove_pending_defferal_listener()

        self._opening_manager.destroy()

    def _read_manual_settings(self, state: State) -> ClimateSettings:
        """Read the manually set values from the state into a ClimateSettings object."""
        target_temperature: float | None = state.attributes.get(ATTR_MANUAL_TARGET_TEMPERATURE)
        target_temperature_low: float | None = state.attributes.get(ATTR_MANUAL_TARGET_TEMPERATURE_LOW)
        target_temperature_high: float | None = state.attributes.get(ATTR_MANUAL_TARGET_TEMPERATURE_HIGH)
        hvac_mode: HVACMode = state.attributes.get(ATTR_MANUAL_HVAC_MODE, self._default_hvac_mode)
        fan_mode: FanMode = state.attributes.get(ATTR_MANUAL_FAN_MODE, self._default_fan_mode)

        return (
            ClimateSettings(
                target_temperature_low,
                target_temperature_high,
                target_temperature,
                hvac_mode,
                fan_mode,
            )
            if (target_temperature_low is not None and target_temperature_high is not None) or target_temperature
            else None
        )
