"""prune_request_logs(): deletes request_logs rows older than the retention period. Run at startup."""

from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.c_database.utcnow import utcnow
from app.core.d_metrics.request_log import RequestLog


def prune_request_logs(db: Session, retention_days: int) -> int:
    result = db.execute(delete(RequestLog).where(RequestLog.created_at < utcnow() - timedelta(days=retention_days)))
    db.commit()
    return result.rowcount
