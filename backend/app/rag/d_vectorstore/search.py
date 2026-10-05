"""search(): the k chunks closest in meaning to a question's embedding, best first, each with a
similarity score (cosine similarity, 1 = identical). Same shape as Track B's search()."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.rag.d_vectorstore.chunk_row import ChunkRow
from app.rag.d_vectorstore.pg_store import PgStore
from app.rag.d_vectorstore.stored_chunk import StoredChunk


def search(store: PgStore, vector, k: int = 4) -> list[tuple[StoredChunk, float]]:
    distance = ChunkRow.embedding.cosine_distance(vector)
    stmt = (
        select(ChunkRow.id, ChunkRow.source, ChunkRow.page, ChunkRow.text, distance.label("distance"))
        .where(ChunkRow.collection == store.collection)
        .order_by(distance)
        .limit(k)
    )
    with Session(store.engine) as db:
        rows = db.execute(stmt).all()
    return [(StoredChunk(r.id, r.source, r.page, r.text), round(1.0 - float(r.distance), 4)) for r in rows]
