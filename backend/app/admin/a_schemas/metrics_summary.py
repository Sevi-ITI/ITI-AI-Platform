"""MetricsSummary: the numbers at the top of the monitoring page, for one time window."""

from pydantic import BaseModel

from app.admin.a_schemas.app_usage import AppUsage
from app.admin.a_schemas.latency_stats import LatencyStats
from app.admin.a_schemas.route_usage import RouteUsage


class MetricsSummary(BaseModel):
    window_minutes: int
    requests: int
    errors: int  # status 500 and above: our problems, not the caller's
    client_errors: int  # status 400-499: the caller's problems (bad key, bad body, ...)
    chats: int
    answered: int
    refused: int  # the "I don't know" reply
    busy_rejections: int  # 503 llm_busy: the queue timed out
    total_ms: LatencyStats
    queue_ms: LatencyStats
    rag_ms: LatencyStats
    ttft_ms: LatencyStats
    by_app: list[AppUsage]
    by_route: list[RouteUsage]
