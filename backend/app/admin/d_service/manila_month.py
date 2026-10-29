"""manila_month(): "2026-10" -> ("2026-10", start, end): that calendar month in Manila time (D-8), as UTC moments.
None = this month. Manila has no daylight saving, so UTC+8 is exact all year (no time zone package needed).
The route has already checked the "YYYY-MM" format."""

from datetime import UTC, datetime, timedelta, timezone

from app.core.c_database.utcnow import utcnow

MANILA = timezone(timedelta(hours=8))

def manila_month(month: str | None) -> tuple[str, datetime, datetime]:
    if month is None:
        now = utcnow().astimezone(MANILA)
        year, number = now.year, now.month

    else:
        year, number = int(month[:4]), int(month[5:])

    starts = datetime(year, number, 1, tzinfo=MANILA)
    ends = datetime(year + number // 12, number % 12 + 1, 1, tzinfo=MANILA)
    return f"{year:04d}-{number:02d}", starts.astimezone(UTC), ends.astimezone(UTC)
