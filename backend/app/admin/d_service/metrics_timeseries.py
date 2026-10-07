"""metrics_timeseries(): requests, errors and timings per time bucket, oldest first, with empty
buckets included so the chart's x-axis is evenly spaced."""

from datetime import UTC, timedelta

from sqlalchemy.orm import Session

from app.admin.a_schemas.timeseries_point import TimeseriesPoint
from app.admin.c_repository.request_logs_since import request_logs_since
from app.admin.d_service.percentile import percentile
from app.core.c_database.utcnow import utcnow


def metrics_timeseries(db: Session, window_minutes: int, bucket_minutes: int) -> list[TimeseriesPoint]:
    size = timedelta(minutes=bucket_minutes)
    now = utcnow()
    first = now - timedelta(minutes=window_minutes)
    first = first.replace(second=0, microsecond=0, minute=first.minute - first.minute % bucket_minutes)
    starts = []
    while first <= now:
        starts.append(first)
        first += size
    buckets: dict = {s: [] for s in starts}
    for r in request_logs_since(db, starts[0]):
        created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=UTC)
        index = int((created - starts[0]) / size)
        if 0 <= index < len(starts):
            buckets[starts[index]].append(r)
    return [
        TimeseriesPoint(
            bucket_start=s,
            requests=len(rows),
            errors=sum(r.status >= 500 for r in rows),
            p50_ms=percentile([r.duration_ms for r in rows], 50),
            p95_ms=percentile([r.duration_ms for r in rows], 95),
            queue_p95_ms=percentile([r.queue_ms for r in rows if r.queue_ms is not None], 95),
        )
        for s, rows in buckets.items()
    ]
