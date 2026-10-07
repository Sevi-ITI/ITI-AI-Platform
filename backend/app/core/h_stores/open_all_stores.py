"""open_all_stores(): makes a store handle for every collection in ITI_COLLECTIONS, at startup.
With pgvector all collections share one table (chunks), told apart by a collection column."""

from app.core.a_config.get_settings import get_settings
from app.core.c_database.get_engine import get_engine
from app.core.h_stores.store_registry import STORES
from app.rag.d_vectorstore.open_store import open_store


def open_all_stores() -> None:
    for name in get_settings().collections:
        STORES[name] = open_store(get_engine(), name)
