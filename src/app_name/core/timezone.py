"""Timezone helpers using the stdlib ``zoneinfo`` module."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Default timezone -- override via settings or env if needed.
DEFAULT_TZ = ZoneInfo("Asia/Shanghai")


def now_utc() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def now_local(tz: ZoneInfo = DEFAULT_TZ) -> datetime:
    """Return the current datetime in the given timezone."""
    return datetime.now(tz)


def to_local(dt: datetime, tz: ZoneInfo = DEFAULT_TZ) -> datetime:
    """Convert a timezone-aware datetime to the given local timezone."""
    return dt.astimezone(tz)
