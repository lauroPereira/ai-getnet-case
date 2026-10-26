"""Single source of time for the application, so relative dates are testable."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

Period = Literal["today", "yesterday", "last_7_days", "next_7_days"]
DEFAULT_TZ = "America/Sao_Paulo"


class Clock(Protocol):
    tz: ZoneInfo

    def now(self) -> datetime: ...


class SystemClock:
    def __init__(self, tz: str = DEFAULT_TZ) -> None:
        self.tz = ZoneInfo(tz)

    def now(self) -> datetime:
        return datetime.now(self.tz)


class FixedClock:
    def __init__(self, at: datetime | str, tz: str = DEFAULT_TZ) -> None:
        self.tz = ZoneInfo(tz)
        parsed = datetime.fromisoformat(at) if isinstance(at, str) else at
        self._at = parsed.replace(tzinfo=self.tz) if parsed.tzinfo is None else parsed.astimezone(self.tz)

    def now(self) -> datetime:
        return self._at


def today(clock: Clock) -> date:
    return clock.now().date()


def resolve_period(period: Period, clock: Clock) -> tuple[date, date]:
    """Inclusive date range for a named period, in the clock's time zone."""
    d = today(clock)
    match period:
        case "today":
            return d, d
        case "yesterday":
            y = d - timedelta(days=1)
            return y, y
        case "last_7_days":
            return d - timedelta(days=6), d
        case "next_7_days":
            return d, d + timedelta(days=6)
    raise ValueError(f"unknown period: {period}")


def add_business_days(start: date, days: int) -> date:
    """Adds business days (Mon-Fri). A start on a weekend counts from the next Monday. No holiday calendar."""
    current = start
    if current.weekday() >= 5:
        current += timedelta(days=7 - current.weekday())
        if days == 0:
            return current
        days -= 1
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current
