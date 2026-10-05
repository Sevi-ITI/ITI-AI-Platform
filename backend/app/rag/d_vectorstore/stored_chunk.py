"""StoredChunk: a chunk as read back from the store (same attribute names as Track B's chunks)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredChunk:
    id: str
    source: str
    page: int | None
    text: str
