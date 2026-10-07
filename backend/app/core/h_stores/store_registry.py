"""STORES: collection name -> its vector store handle. Filled once at startup by open_all_stores()."""

from app.rag.d_vectorstore.pg_store import PgStore

STORES: dict[str, PgStore] = {}
