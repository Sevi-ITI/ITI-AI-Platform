"""collection_infos(): each collection with its uploads, searchable chunk count and owning company."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.c_repository.count_documents import count_documents
from app.core.a_config.get_settings import get_settings
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.store_registry import STORES
from app.rag.d_vectorstore.count_chunks import count_chunks


def collection_infos(db: Session) -> list[CollectionInfo]:
    docs, in_settings = count_documents(db), set(get_settings().collections)
    owners = {name: company for name, company in db.execute(select(CollectionRow.name, CollectionRow.company_id))}
    return [
        CollectionInfo(
            name=name,
            documents=docs.get(name, 0),
            chunks=count_chunks(store),
            in_settings=name in in_settings,
            company_id=owners.get(name),
        )
        for name, store in STORES.items()
    ]
