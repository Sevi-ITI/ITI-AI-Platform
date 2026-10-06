"""utcnow(): the current time in UTC, with its time zone attached."""

from datetime import datetime, UTC

def utcnow() -> datetime:
    return datetime.now(UTC)