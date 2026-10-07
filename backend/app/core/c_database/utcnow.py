"""utcnow(): the current time in UTC, with its time zone attached."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)
