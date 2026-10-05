"""count_chunks(): how many chunks a collection holds (Track B: store.count())."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.rag.d_vectorstore.chunk_row import ChunkRow
from app.rag.d_vectorstore.pg_store import PgStore


def count_chunks(store: PgStore) -> int:
    with Session(store.engine) as db:
        return db.scalar(select(func.count()).select_from(ChunkRow).where(ChunkRow.collection == store.collection))
