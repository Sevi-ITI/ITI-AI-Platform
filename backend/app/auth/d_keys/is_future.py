"""is_future(): is this moment still ahead of now? None = no. Used for session expiry and account lockout."""

from datetime import UTC, datetime


def is_future(moment: datetime | None) -> bool:
    if moment is None:
        return False
    if moment.tzinfo is None:  # SQLite (tests) drops the time zone; Postgres keeps it
        moment = moment.replace(tzinfo=UTC)
    return moment > datetime.now(UTC)
