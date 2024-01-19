"""Opening Manager Class."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from homeassistant.core import HomeAssistant, State, Event, CALLBACK_TYPE
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_point_in_utc_time,
)
from homeassistant.const import (
    STATE_ON,
    STATE_OPEN,
)

from .const import _LOGGER


class Opening:
    """Opening class used for tracking information about an opening entity."""

    entity_id: str
    delay: timedelta
    is_open: bool
    remove_pending_delay_listener: CALLBACK_TYPE | None

    def __init__(self, entity_id: str, delay: timedelta):
        """Initialize a new instance of the Opening class."""

        self.delay = delay
        self.entity_id = entity_id


class OpeningManager:
    """Manager for tracking the state of any openings such as doors or windows."""

    _is_initialized: bool = False
    _is_any_opening_open: bool
    _openings: dict[str, Opening]
    _hass: HomeAssistant | None
    _remove_state_change_listener: CALLBACK_TYPE | None = None
    _on_change_callback: Callable[[bool], None] | None = None

    def __init__(
        self,
        opening_configs: list[tuple[str, timedelta | None]] | None,
        default_delay: timedelta,
    ):
        """Initialize a new instance of the OpeningManager class."""
        self._openings = dict[str, Opening]()

        # Setup the opening dictionary from the config tuples
        for opening_config in opening_configs:
            entity_id, delay = opening_config
            self._openings[entity_id] = Opening(entity_id, delay or default_delay)

    def initialize(self, hass: HomeAssistant, on_change_callback: Callable[[bool], None]) -> None:
        """Initialize the manage."""

        if self._is_initialized is True:
            raise RuntimeError("Manager has already been initialized")

        self._hass = hass
        self._on_change_callback = on_change_callback
        opening_entity_ids: list[str] = list[str]()

        # Set the initial opening states
        for opening in self._openings.values():
            opening.is_open = self._is_opening_open(opening)
            opening_entity_ids.append(opening.entity_id)

        # Set the initial state
        self._is_any_opening_open = any(o.is_open for o in self._openings.values())

        # If there are any openings, add a state change listener for them
        if len(opening_entity_ids) > 0:
            self._remove_state_change_listener = async_track_state_change_event(
                self._hass, opening_entity_ids, self._async_on_opening_entity_changed
            )

        self._is_initialized = True

    def destroy(self) -> None:
        """Cleanup manager resources."""

        self._hass = None

        # Remove the state change listener if it's been set
        if self._remove_state_change_listener is not None:
            self._remove_state_change_listener()

        for opening in self._openings.values():
            # If the opening has a pending delay, remove the listener
            if opening.remove_pending_delay_listener is not None:
                opening.remove_pending_delay_listener()

    @property
    def is_any_opening_open(self) -> bool:
        """A flag indicating if any openings are open."""
        return self._is_any_opening_open

    async def _async_on_opening_entity_changed(self, event: Event) -> None:
        entity_id: str = event.data.get("entity_id")
        opening: Opening = self._openings.get(entity_id)

        _LOGGER.debug("Opening %s state changed, beginning delay", opening.entity_id)

        # Remove any existing listener
        if opening.remove_pending_delay_listener is not None:
            _LOGGER.debug("An existing delay listener exists, removing it")
            opening.remove_pending_delay_listener()

        point_in_time: datetime = datetime.now(timezone.utc) + opening.delay

        async def async_update_action() -> None:
            await self._async_update_opening(opening)

        opening.remove_pending_delay_listener = async_track_point_in_utc_time(self._hass, async_update_action, point_in_time)

    async def _async_update_opening(self, opening: Opening) -> None:
        """Update the given opening and check if the overall state has changed."""
        opening.is_open = self._is_opening_open(opening)
        is_any_opening_open = any(o.is_open for o in self._openings.values())

        if self._is_any_opening_open != is_any_opening_open:
            self._is_any_opening_open = is_any_opening_open

            if self._on_change_callback is not None:
                await self._on_change_callback(is_any_opening_open)

    def _is_opening_open(self, opening: Opening) -> bool:
        opening_state: State | None = self._hass.states.get(opening.entity_id)
        return opening_state in [STATE_OPEN, STATE_ON] if opening_state is not None else False
