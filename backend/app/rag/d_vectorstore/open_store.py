"""open_store(): the store handle for one collection (replaces Track B's open_store(path))."""

from sqlalchemy.engine import Engine

from app.rag.d_vectorstore.pg_store import PgStore


def open_store(engine: Engine, collection: str) -> PgStore:
    return PgStore(engine=engine, collection=collection)
