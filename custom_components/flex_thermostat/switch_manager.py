"""The Switch Manager class."""

import asyncio
from collections.abc import Callable
from homeassistant.helpers.event import (
    async_track_state_change_event,
)
from homeassistant.core import (
    HomeAssistant,
    Event,
    State,
    CALLBACK_TYPE,
    DOMAIN as HA_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from .const import _LOGGER


class SwitchManager:
    """Manager for controlling and tracking a switch entity."""

    _id: str
    _is_active: bool
    _is_enabled: bool
    _hass: HomeAssistant | None
    _is_initialized: bool = False
    _remove_state_change_listener: CALLBACK_TYPE | None = None
    _on_change_callback: Callable[[bool], None] | None = None

    def __init__(self, entity_id: str):
        """Initialize a SwitchManager instance."""

        self._id = entity_id
        self._is_enabled = entity_id is not None

    @property
    def entity_id(self) -> str:
        """Returns the id of the switch."""
        return self._id

    @property
    def is_active(self) -> bool:
        """Gets a flag indicating if the switch is active (on)."""

        if self._is_initialized is False:
            raise RuntimeError("Switch has not been initialized")

        return self._is_enabled and self._is_active

    @property
    def is_enabled(self) -> bool:
        """Gets a flag indicating if the switch is enabled."""
        return self._is_enabled

    def initialize(self, hass: HomeAssistant, on_change_callback: Callable[[bool], None]):
        """Initialize the switch manager to track the switch state."""

        if self._is_initialized is True:
            raise RuntimeError("Switch has already been initialized")
        elif on_change_callback is None:
            raise RuntimeError("The change callback is required")

        self._hass = hass
        self._on_change_callback = on_change_callback

        if self._is_enabled is True:
            self._is_active = self._is_switch_on()

            self._remove_state_change_listener = async_track_state_change_event(
                self._hass, self._id, self._async_on_state_changed
            )
        else:
            self._is_active = False

        self._is_initialized = True

    def destroy(self) -> None:
        """Cleanup manager resources."""

        if self._is_initialized is False:
            raise RuntimeError("Switch has not been initialized")

        self._hass = None

        if self._remove_state_change_listener is not None:
            self._remove_state_change_listener()

    async def async_turn_on(self) -> None:
        """Turn the switch on."""
        if self._is_initialized is False:
            raise RuntimeError("Switch has not been initialized")

        if self._is_enabled is True and self._is_active is False:
            self._is_active = False
            await self._hass.services.async_call(HA_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: self._id})

    async def async_turn_off(self) -> None:
        """Turn the switch off."""
        if self._is_initialized is False:
            raise RuntimeError("Switch has not been initialized")

        if self._is_enabled is True and self._is_active is True:
            self._is_active = False
            await self._hass.services.async_call(HA_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: self._id})

    async def _async_on_state_changed(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        is_active = new_state.state == STATE_ON if new_state is not None else False

        if self._is_active != is_active:
            _LOGGER.debug(
                "Switch %s changed state to %s which differs from current state, triggering callback",
                self._id,
                is_active,
            )
            self._is_active = is_active
            if asyncio.iscoroutinefunction(self._on_change_callback):
                await self._on_change_callback(self._is_active)
            else:
                self._on_change_callback(self._is_active)
        else:
            _LOGGER.debug(
                "Switch %s changed state to %s which matches current state",
                self._id,
                is_active,
            )

    def _is_switch_on(self) -> bool:
        entity_state: State | None = self._hass.states.get(self._id)
        return entity_state.state == STATE_ON if entity_state is not None else False
