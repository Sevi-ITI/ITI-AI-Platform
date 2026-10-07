"""request_logs_since(): every request log row since a moment, oldest first (for metrics).
Capped at 50,000 rows: about a week of steady pilot traffic, and still fast to summarise."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.d_metrics.request_log import RequestLog

CAP = 50_000


def request_logs_since(db: Session, since: datetime) -> list[RequestLog]:
    return list(db.scalars(select(RequestLog).where(RequestLog.created_at >= since).order_by(RequestLog.id).limit(CAP)))
