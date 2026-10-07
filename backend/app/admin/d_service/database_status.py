"""database_status(): can we reach Postgres, and how long did SELECT 1 take?"""

import time

from sqlalchemy.orm import Session

from app.admin.a_schemas.component_health import ComponentHealth
from app.admin.c_repository.ping_database import ping_database


def database_status(db: Session) -> ComponentHealth:
    start = time.perf_counter()
    try:
        ping_database(db)
    except Exception as exc:
        return ComponentHealth(ok=False, latency_ms=None, detail=f"{type(exc).__name__}: {exc}"[:200])
    return ComponentHealth(ok=True, latency_ms=int((time.perf_counter() - start) * 1000), detail="PostgreSQL reachable")
