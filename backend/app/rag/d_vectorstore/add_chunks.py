"""add_chunks(): saves chunks and their embeddings. A chunk id that already exists in the
collection is replaced (upsert), the same behaviour as Track B's Chroma store."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.rag.d_vectorstore.chunk_row import ChunkRow
from app.rag.d_vectorstore.pg_store import PgStore


def add_chunks(store: PgStore, chunks, vectors) -> int:
    rows = [
        {"collection": store.collection, "id": c.id, "source": c.source, "page": c.page, "text": c.text, "embedding": v}
        for c, v in zip(chunks, vectors, strict=True)
    ]
    if not rows:
        return 0
    stmt = insert(ChunkRow).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["collection", "id"],
        set_={k: stmt.excluded[k] for k in ("source", "page", "text", "embedding")},
    )
    with Session(store.engine) as db:
        db.execute(stmt)
        db.commit()
    return len(rows)
