"""The Cycle Manager class."""

from datetime import datetime, timedelta, timezone


class CycleManager:
    """Manager for tracking on/off cycles."""

    _min_runtime: timedelta | None
    _min_cooldown: timedelta | None
    _last_start: datetime | None = None
    _last_stop: datetime | None = None
    _is_initialized: bool = False

    def __init__(
        self, min_runtime: timedelta | None, min_cooldown: timedelta | None
    ) -> None:
        """Initialize a new instance of the CycleManager class."""

        self._min_runtime = min_runtime
        self._min_cooldown = min_cooldown

    def initialize(
        self, last_start: datetime | None, last_stop: datetime | None
    ) -> None:
        """Prepare the manager for usage."""
        self._last_start = last_start
        self._last_stop = last_stop
        self._is_initialized = True

    @property
    def last_stop(self) -> datetime | None:
        """Get the timestamp of the last cycle stop."""
        return self._last_stop

    @property
    def last_start(self) -> datetime | None:
        """Get the timestamp of the last cycle start."""
        return self._last_start

    @property
    def can_start(self) -> bool:
        """Returns a flag indicating if a cycle can start."""
        if self._is_initialized is False:
            raise RuntimeError("Manager has not been initialized")

        return (
            self._last_stop is None
            or self._min_cooldown is None
            or self._last_stop + self._min_cooldown <= datetime.now(timezone.utc)
        )

    @property
    def can_stop(self) -> bool:
        """Returns a flag indicating if a cycle can stop."""
        if self._is_initialized is False:
            raise RuntimeError("Manager has not been initialized")

        return (
            self._last_start is None
            or self._min_runtime is None
            or self._last_start + self._min_runtime <= datetime.now(timezone.utc)
        )

    @property
    def remaining_start_time(self) -> timedelta:
        """Returns the timedelta for when the next cycle can start."""

        if self._is_initialized is False:
            raise RuntimeError("Manager has not been initialized")
        elif self._last_stop is None:
            raise RuntimeError("Can't get a remaining time if a cycle hasn't started")
        elif self._min_cooldown is None:
            raise RuntimeError("Can't get a remaining time without a minimum cooldown")

        return (self._last_stop + self._min_cooldown) - datetime.now(timezone.utc)

    @property
    def remaining_stop_time(self) -> timedelta:
        """Returns the timedelta for when the next cycle can stop."""

        if self._is_initialized is False:
            raise RuntimeError("Manager has not been initialized")
        elif self._last_start is None:
            raise RuntimeError("Can't get a remaining time if a cycle hasn't started")
        elif self._min_runtime is None:
            raise RuntimeError("Can't get a remaining time without a minimum runtime")

        return (self._last_start + self._min_runtime) - datetime.now(timezone.utc)

    def cycle_started(self) -> None:
        """Update the last started time to the current time."""
        self._last_start = datetime.now(timezone.utc)

    def cycle_ended(self) -> None:
        """Update the last stopped time to the current time."""
        self._last_stop = datetime.now(timezone.utc)
