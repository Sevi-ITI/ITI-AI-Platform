"""latency_stats(): count, p50, p95 and max of a list of millisecond timings (None values skipped)."""

from app.admin.a_schemas.latency_stats import LatencyStats
from app.admin.d_service.percentile import percentile


def latency_stats(values: list[int | None]) -> LatencyStats:
    clean = [v for v in values if v is not None]
    return LatencyStats(
        count=len(clean), p50=percentile(clean, 50), p95=percentile(clean, 95), max=max(clean) if clean else None
    )
