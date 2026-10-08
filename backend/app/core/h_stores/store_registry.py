"""STORES: collection name -> its vector store handle. Filled at startup by open_all_stores(); a collection
created later is added by create_collection(). ponytail: one process only; with several workers, another
worker would not see a new collection until restart (read the table on a miss then)."""

from app.rag.d_vectorstore.pg_store import PgStore

STORES: dict[str, PgStore] = {}
