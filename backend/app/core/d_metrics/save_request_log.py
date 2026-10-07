"""save_request_log(): writes one request_logs row from the request's metrics dict.
Never raises: a logging problem must not break the answer the caller already received."""

import logging

from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.d_metrics.request_log import RequestLog

log = logging.getLogger(__name__)
COLUMNS = set(RequestLog.__table__.columns.keys()) - {"id", "created_at"}

def save_request_log(metrics: dict) -> None:
    try:
        with get_sessionmaker()() as db:
            db.add(RequestLog(**{k: v for k, v in metrics.items() if k in COLUMNS}))
            db.commit()
    except Exception:
        log.exception("Could not save the request log row.")

