"""gpu_status(): GPU memory and load from nvidia-smi, or None where there is no NVIDIA GPU."""

import shutil
import subprocess

from app.admin.a_schemas.gpu_info import GpuInfo

QUERY = "--query-gpu=name,memory.used,memory.total,utilization.gpu"


def gpu_status() -> GpuInfo | None:
    exe = shutil.which("nvidia-smi")
    if exe is None:
        return None
    try:
        out = subprocess.run([exe, QUERY, "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
        name, used, total, util = (part.strip() for part in out.stdout.splitlines()[0].split(","))
        return GpuInfo(name=name, memory_used_mb=int(used), memory_total_mb=int(total), utilization_pct=int(util))
    except Exception:
        return None
