"""TimeseriesPoint: one time bucket of the monitoring charts."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class TimeseriesPoint(BaseModel):
    bucket_start: UtcDateTime
    requests: int
    errors: int
    p50_ms: int | None
    p95_ms: int | None
    queue_p95_ms: int | None
