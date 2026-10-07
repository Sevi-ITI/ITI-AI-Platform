"""Passage: what prompts, citations and the answer check need from a piece of a document.
Both b_splitter.Chunk (fresh from a PDF) and d_vectorstore.StoredChunk (from PostgreSQL) match it."""
from typing import Protocol


class Passage(Protocol):
    @property
    def source(self) -> str: ...

    @property
    def page(self) -> int | None: ...

    @property
    def text(self) -> str: ...
