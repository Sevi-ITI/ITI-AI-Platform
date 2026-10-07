"""get_store(): the open vector store for a collection, or 404 collection_not_found."""

from app.core.e_errors.app_error import AppError
from app.core.h_stores.store_registry import STORES
from app.rag.d_vectorstore.pg_store import PgStore


def get_store(collection: str) -> PgStore:
    try:
        return STORES[collection]
    except KeyError:
        raise AppError(404, "collection_not_found", f"No collection named '{collection}'.") from None
