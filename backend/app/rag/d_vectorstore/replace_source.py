"""replace_source(): swaps one file's chunks for its new version in ONE transaction.
The old chunks are deleted and the new ones inserted together: if anything fails, nothing changes,
so a re-upload can never leave a document with no chunks (or with half old, half new)."""

from collections.abc import Sequence

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.rag.b_splitter import Chunk
from app.rag.d_vectorstore.chunk_row import ChunkRow
from app.rag.d_vectorstore.pg_store import PgStore


def replace_source(store: PgStore, source: str, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> int:
    rows = [
        {"collection": store.collection, "id": c.id, "source": c.source, "page": c.page, "text": c.text, "embedding": v}
        for c, v in zip(chunks, vectors, strict=True)
    ]
    with Session(store.engine) as db, db.begin():  # commits at the end, or rolls everything back on any error
        db.execute(delete(ChunkRow).where(ChunkRow.collection == store.collection, ChunkRow.source == source))
        if rows:
            db.execute(insert(ChunkRow), rows)
    return len(rows)