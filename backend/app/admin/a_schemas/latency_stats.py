"""LatencyStats: count, median (p50), 95th percentile (p95) and maximum, in milliseconds.
p95 = 95 of every 100 requests were at least this fast; it shows the slow tail the median hides."""

from pydantic import BaseModel


class LatencyStats(BaseModel):
    count: int
    p50: int | None
    p95: int | None
    max: int | None
