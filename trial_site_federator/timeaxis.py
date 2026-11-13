"""Calendar helpers shared by freshness, recruitment exposure and feasibility.

Months are represented as ``YYYY-MM`` strings.  The project deliberately keeps a
single representation so that an observation month, an ``as_of`` date and a
forecast horizon cannot drift apart between stages.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Iterable

from trial_site_federator.runtime import DomainError


def parse_month(value: object) -> tuple[int, int]:
    text = str(value or "").strip()
    parts = text.split("-")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise DomainError(f"invalid month: {value!r}")
    try:
        year, month = int(parts[0]), int(parts[1])
    except ValueError:
        raise DomainError(f"invalid month: {value!r}") from None
    if not 1 <= month <= 12:
        raise DomainError(f"invalid month: {value!r}")
    return year, month


def format_month(year: int, month: int) -> str:
    while month > 12:
        year, month = year + 1, month - 12
    while month < 1:
        year, month = year - 1, month + 12
    return f"{year:04d}-{month:02d}"


def parse_date(value: object) -> date:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise DomainError(f"invalid date: {value!r}") from None


def month_start(month: str) -> date:
    year, number = parse_month(month)
    return date(year, number, 1)


def month_end(month: str) -> date:
    year, number = parse_month(month)
    return date(year, number, calendar.monthrange(year, number)[1])


def days_in_month(month: str) -> int:
    year, number = parse_month(month)
    return calendar.monthrange(year, number)[1]


def add_months(month: str, offset: int) -> str:
    year, number = parse_month(month)
    return format_month(year, number + int(offset))


def month_of(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def month_distance(earlier: str, later: str) -> int:
    """Number of calendar months from ``earlier`` to ``later`` (later - earlier)."""
    ey, em = parse_month(earlier)
    ly, lm = parse_month(later)
    return (ly - ey) * 12 + (lm - em)


def next_months(month: str, count: int) -> list[str]:
    if count < 0:
        raise DomainError("month count must be non-negative")
    return [add_months(month, index + 1) for index in range(count)]


def month_span(start: str, count: int) -> list[str]:
    return [add_months(start, index) for index in range(count)]


def latest_month(months: Iterable[str]) -> str | None:
    values = sorted(str(value) for value in months)
    return values[-1] if values else None


def date_range(start: date, end: date) -> int:
    return (end - start).days + 1


def report_lag_days(month: str, known_at: date) -> int:
    """Days between the month end and the reporting date.

    A negative value means the record was reported before the month closed,
    which is allowed by the fixtures but is still recorded for transparency.
    """
    return (known_at - month_end(month)).days


def within_days(earlier: date, later: date, limit: int) -> bool:
    return 0 <= (later - earlier).days <= limit


def day_after(value: date) -> date:
    return value + timedelta(days=1)
