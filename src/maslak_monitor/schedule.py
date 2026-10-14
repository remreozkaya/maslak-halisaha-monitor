"""Weekly observation window in Istanbul civil time."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo('Europe/Istanbul')

@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime
    week_start: date


def _local(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError('Timezone-aware datetime required')
    return now.astimezone(ISTANBUL)


def _from_friday(day: date) -> Window:
    start = datetime(day.year, day.month, day.day, 10, tzinfo=ISTANBUL)
    end = start + timedelta(days=3)
    return Window(start, end, end.date())


def window_at(now: datetime) -> Window | None:
    local = _local(now)
    friday = local.date() - timedelta(days=(local.weekday() - 4) % 7)
    window = _from_friday(friday)
    return window if window.start <= local <= window.end else None


def next_window(now: datetime) -> Window:
    local = _local(now)
    active = window_at(local)
    if active:
        return active
    friday = local.date() + timedelta(days=(4 - local.weekday()) % 7)
    window = _from_friday(friday)
    if window.start < local:
        window = _from_friday(friday + timedelta(days=7))
    return window
