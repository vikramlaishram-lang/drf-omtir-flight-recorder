from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


class ObserverUnavailableError(RuntimeError):
    """Raised when observer health is required but unavailable or stale."""


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


@dataclass(frozen=True)
class RuntimeHealth:
    observer_required: bool = False
    observer_last_heartbeat_at: dt.datetime | None = None
    observer_heartbeat_ttl_seconds: int = 5

    def observer_is_current(self, *, now: dt.datetime | None = None) -> bool:
        if not self.observer_required:
            return True

        if self.observer_last_heartbeat_at is None:
            return False

        current = now or utc_now()
        age = current - self.observer_last_heartbeat_at

        return age.total_seconds() <= self.observer_heartbeat_ttl_seconds

    def require_observer_current(self, *, now: dt.datetime | None = None) -> None:
        if not self.observer_is_current(now=now):
            raise ObserverUnavailableError("observer_unavailable")
