"""HealthReport: everything the admin overview needs to say "all good" or point at the problem."""

from typing import Literal

from pydantic import BaseModel

from app.admin.a_schemas.component_health import ComponentHealth
from app.admin.a_schemas.gpu_info import GpuInfo
from app.admin.a_schemas.loaded_model import LoadedModel
from app.admin.a_schemas.slot_info import SlotInfo


class HealthReport(BaseModel):
    status: Literal["ok", "degraded"]
    uptime_s: int
    database: ComponentHealth
    ollama: ComponentHealth
    models: list[LoadedModel]
    gpu: GpuInfo | None
    llm_slots: SlotInfo
    ingest_busy: bool
