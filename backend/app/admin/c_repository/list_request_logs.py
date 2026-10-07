"""list_request_logs(): request log rows, newest first, with optional filters."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.d_metrics.request_log import RequestLog


def list_request_logs(
    db: Session, app_id: str | None, user_id: str | None, errors_only: bool, limit: int, offset: int
) -> list[RequestLog]:
    stmt = select(RequestLog).order_by(RequestLog.id.desc()).limit(limit).offset(offset)
    if app_id:
        stmt = stmt.where(RequestLog.app_id == app_id)
    if user_id:
        stmt = stmt.where(RequestLog.user_id == user_id)
    if errors_only:
        # status >= 400, plus streams that failed after their 200 (status 200 with an error_code)
        stmt = stmt.where(or_(RequestLog.status >= 400, RequestLog.error_code.is_not(None)))
    return list(db.scalars(stmt))
