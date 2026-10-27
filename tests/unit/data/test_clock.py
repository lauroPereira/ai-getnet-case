from datetime import UTC, date, datetime

import pytest

from merchant_assistant.data.clock import FixedClock, add_business_days, resolve_period, today


def test_fixed_clock_uses_sao_paulo_time_zone():
    clock = FixedClock(datetime(2026, 10, 27, 1, 30, tzinfo=UTC))
    # 01:30 UTC is still the previous day in São Paulo (UTC-3).
    assert today(clock) == date(2026, 10, 26)


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        ("today", (date(2026, 10, 26), date(2026, 10, 26))),
        ("yesterday", (date(2026, 10, 25), date(2026, 10, 25))),
        ("last_7_days", (date(2026, 10, 20), date(2026, 10, 26))),
        ("next_7_days", (date(2026, 10, 26), date(2026, 11, 1))),
    ],
)
def test_resolve_period(period, expected):
    assert resolve_period(period, FixedClock("2026-10-26T10:00:00")) == expected


@pytest.mark.parametrize(
    ("start", "days", "expected"),
    [
        (date(2026, 10, 23), 1, date(2026, 10, 26)),  # Friday + 1 -> Monday
        (date(2026, 10, 25), 1, date(2026, 10, 26)),  # Sunday + 1 -> Monday
        (date(2026, 10, 25), 2, date(2026, 10, 27)),  # Sunday + 2 -> Tuesday
        (date(2026, 10, 24), 2, date(2026, 10, 27)),  # Saturday + 2 -> Tuesday
        (date(2026, 10, 26), 2, date(2026, 10, 28)),
        (date(2026, 10, 24), 0, date(2026, 10, 26)),
    ],
)
def test_add_business_days(start, days, expected):
    assert add_business_days(start, days) == expected
