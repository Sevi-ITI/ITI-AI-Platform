"""delete_source(): removes every chunk of one file from a collection. Returns how many went."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.rag.d_vectorstore.chunk_row import ChunkRow
from app.rag.d_vectorstore.pg_store import PgStore


def delete_source(store: PgStore, source: str) -> int:
    with Session(store.engine) as db:
        result = db.execute(delete(ChunkRow).where(ChunkRow.collection == store.collection, ChunkRow.source == source))
        db.commit()
        return result.rowcount
