"""Datetime contract for the API.

Storage convention: every timestamp is written as *naive UTC* (`datetime.utcnow()` / DateTime columns
without a time zone, identical on PostgreSQL and SQLite).

Wire convention: every timestamp leaves the API as ISO-8601 in UTC with a trailing "Z"
(e.g. 2027-10-03T15:43:09.719546Z), so browsers parse it as UTC instead of local time.

`z()` therefore reads a naive value as UTC (true by the storage convention) and converts an aware
value to UTC first; it never relabels a non-UTC aware time as UTC.
"""
from datetime import datetime, timezone
from typing import Annotated

from pydantic import PlainSerializer


def as_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def z(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return as_utc_naive(value).isoformat() + "Z"


UtcDateTime = Annotated[datetime, PlainSerializer(z, return_type=str, when_used="json")]
OptUtcDateTime = Annotated[datetime | None, PlainSerializer(z, return_type=str | None, when_used="json")]
