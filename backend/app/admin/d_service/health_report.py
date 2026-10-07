"""health_report(): one call that answers "is everything up?" for the admin overview."""

import time

from sqlalchemy.orm import Session

from app.admin.a_schemas.health_report import HealthReport
from app.admin.a_schemas.slot_info import SlotInfo
from app.admin.d_service.database_status import database_status
from app.admin.d_service.gpu_status import gpu_status
from app.admin.d_service.ollama_status import ollama_status
from app.core.d_metrics.started_at import STARTED_AT
from app.core.g_llm_slots.get_slot_state import get_slot_state
from app.core.g_llm_slots.ingest_lock import INGEST_LOCK


def health_report(db: Session) -> HealthReport:
    database = database_status(db)
    ollama, models = ollama_status()
    slots = get_slot_state()
    return HealthReport(
        status="ok" if database.ok and ollama.ok else "degraded",
        uptime_s=int(time.time() - STARTED_AT),
        database=database,
        ollama=ollama,
        models=models,
        gpu=gpu_status(),
        llm_slots=SlotInfo(limit=slots.limit, running=slots.running, waiting=slots.waiting),
        ingest_busy=INGEST_LOCK.locked(),
    )
