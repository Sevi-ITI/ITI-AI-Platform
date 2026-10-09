"""collection_infos(): each collection with its uploads and searchable chunk count."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.c_repository.count_documents import count_documents
from app.core.a_config.get_settings import get_settings
from app.core.h_stores.store_registry import STORES
from app.rag.d_vectorstore.count_chunks import count_chunks


def collection_infos(db: Session) -> list[CollectionInfo]:
    docs, in_settings = count_documents(db), set(get_settings().collections)
    return [
        CollectionInfo(
            name=name, documents=docs.get(name, 0), chunks=count_chunks(store), in_settings=name in in_settings
        )
        for name, store in STORES.items()
    ]
