"""metrics_summary(): the monitoring page's headline numbers for the last `window_minutes`."""

from collections import defaultdict
from datetime import timedelta

from sqlalchemy.orm import Session

from app.admin.a_schemas.app_usage import AppUsage
from app.admin.a_schemas.metrics_summary import MetricsSummary
from app.admin.a_schemas.route_usage import RouteUsage
from app.admin.c_repository.request_logs_since import request_logs_since
from app.admin.d_service.latency_stats import latency_stats
from app.admin.d_service.percentile import percentile
from app.core.c_database.utcnow import utcnow

CHAT_ROUTES = {"/v1/chat", "/v1/chat/stream"}


def metrics_summary(db: Session, window_minutes: int) -> MetricsSummary:
    rows = request_logs_since(db, utcnow() - timedelta(minutes=window_minutes))
    chats = [r for r in rows if r.route in CHAT_ROUTES]
    apps, routes = defaultdict(lambda: [0, 0]), defaultdict(list)
    for r in rows:
        if r.app_id:
            apps[r.app_id][0] += 1
            apps[r.app_id][1] += r.status >= 500
        routes[r.route or r.path].append(r)
    return MetricsSummary(
        window_minutes=window_minutes,
        requests=len(rows),
        errors=sum(r.status >= 500 for r in rows),
        client_errors=sum(400 <= r.status < 500 for r in rows),
        chats=len(chats),
        answered=sum(r.found is True for r in chats),
        refused=sum(r.found is False for r in chats),
        busy_rejections=sum(r.error_code == "llm_busy" for r in rows),
        total_ms=latency_stats([r.duration_ms for r in chats]),
        queue_ms=latency_stats([r.queue_ms for r in chats]),
        rag_ms=latency_stats([r.rag_ms for r in chats]),
        ttft_ms=latency_stats([r.ttft_ms for r in chats]),
        by_app=sorted(
            (AppUsage(app_id=a, requests=n, errors=e) for a, (n, e) in apps.items()), key=lambda u: -u.requests
        ),
        by_route=sorted(
            (
                RouteUsage(
                    route=k,
                    requests=len(v),
                    errors=sum(r.status >= 500 for r in v),
                    p95_ms=percentile([r.duration_ms for r in v], 95),
                )
                for k, v in routes.items()
            ),
            key=lambda u: -u.requests,
        ),
    )
