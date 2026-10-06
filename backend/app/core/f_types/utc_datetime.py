"""UtcDateTime: a datetime that always leaves as "...Z" (UTC), so every caller reads the same instant.

Why both branches: Postgres hands back datetimes in ITS session time zone (on a Manila server that
is +08:00), and SQLite, used in the tests, hands back naive ones that are really UTC."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator

UtcDateTime = Annotated[datetime, AfterValidator(lambda v: v.astimezone(UTC) if v.tzinfo else v.replace(tzinfo=UTC))]