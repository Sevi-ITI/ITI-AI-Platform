"""LoadedModel: a model Ollama currently holds in memory, and how much of it is on the GPU."""

from pydantic import BaseModel


class LoadedModel(BaseModel):
    name: str
    size_mb: int
    vram_mb: int
