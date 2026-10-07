"""ollama_status(): is Ollama up (its version), and which models are loaded right now (/api/ps)."""

import time

import httpx

from app.admin.a_schemas.component_health import ComponentHealth
from app.admin.a_schemas.loaded_model import LoadedModel
from app.core.a_config.get_settings import get_settings


def ollama_status() -> tuple[ComponentHealth, list[LoadedModel]]:
    base, start = get_settings().ollama_url.rstrip("/"), time.perf_counter()
    try:
        with httpx.Client(timeout=2.0) as client:
            version = client.get(f"{base}/api/version").json().get("version", "?")
            loaded = client.get(f"{base}/api/ps").json().get("models", [])
    except Exception as exc:
        return ComponentHealth(ok=False, latency_ms=None, detail=f"Ollama unreachable: {type(exc).__name__}"), []
    models = [
        LoadedModel(name=m.get("name", "?"), size_mb=m.get("size", 0) // 2**20, vram_mb=m.get("size_vram", 0) // 2**20)
        for m in loaded
    ]
    health = ComponentHealth(ok=True, latency_ms=int((time.perf_counter() - start) * 1000), detail=f"Ollama {version}")
    return health, models
