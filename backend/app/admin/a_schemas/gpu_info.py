"""GpuInfo: the GPU's memory and load, read from nvidia-smi."""

from pydantic import BaseModel


class GpuInfo(BaseModel):
    name: str
    memory_used_mb: int
    memory_total_mb: int
    utilization_pct: int
