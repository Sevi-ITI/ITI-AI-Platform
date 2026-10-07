"""ComponentHealth: is one dependency (database, Ollama) reachable, and how fast it answered."""

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    ok: bool
    latency_ms: int | None
    detail: str
