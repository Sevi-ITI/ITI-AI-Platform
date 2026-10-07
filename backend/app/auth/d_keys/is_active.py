"""is_active(): False if the key is revoked or past its expiry date."""

from datetime import UTC, datetime


def is_active(revoked_at: datetime | None, expires_at: datetime | None) -> bool:
    if revoked_at is not None:
        return False
    if expires_at is None:
        return True
    if expires_at.tzinfo is None:  # SQLite (tests) drops the time zone; Postgres keeps it
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > datetime.now(UTC)
