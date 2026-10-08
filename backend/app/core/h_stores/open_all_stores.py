"""open_all_stores(): at startup, adds any ITI_COLLECTIONS name missing from the collections table, then makes a
store handle for every row. With pgvector all collections share one table (chunks), told apart by a collection column."""

from sqlalchemy import select

from app.core.a_config.get_settings import get_settings
from app.core.c_database.get_engine import get_engine
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.store_registry import STORES
from app.rag.d_vectorstore.open_store import open_store


def open_all_stores() -> None:
    STORES.clear()
    with get_sessionmaker()() as db:
        known = set(db.scalars(select(CollectionRow.name)))
        db.add_all(CollectionRow(name=n) for n in get_settings().collections if n not in known)
        db.commit()
        for name in db.scalars(select(CollectionRow.name).order_by(CollectionRow.created_at, CollectionRow.name)):
            STORES[name] = open_store(get_engine(), name)
