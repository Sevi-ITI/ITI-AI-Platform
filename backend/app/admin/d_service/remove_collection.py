"""remove_collection(): deletes an EMPTY collection that is not in ITI_COLLECTIONS, and takes it off every key.
404 collection_not_found; 409 collection_in_settings (startup would re-create it); 409 collection_not_empty
(documents, passages or an upload in progress: delete its documents first). Old chats in it stay as history."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_deleted import CollectionDeleted
from app.admin.c_repository.count_documents import count_documents
from app.auth.c_repository.list_keys import list_keys
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.store_registry import STORES
from app.rag.d_vectorstore.count_chunks import count_chunks


def remove_collection(db: Session, name: str) -> CollectionDeleted:
    row = db.get(CollectionRow, name)
    if row is None or name not in STORES:
        raise AppError(404, "collection_not_found", f"No collection named '{name}'.")
    if name in get_settings().collections:
        raise AppError(
            409,
            "collection_in_settings",
            f"'{name}' is listed in the server settings (ITI_COLLECTIONS) and would come back at the next restart. "
            "Remove it there first.",
        )
    if count_documents(db).get(name, 0) or count_chunks(STORES[name]):
        raise AppError(409, "collection_not_empty", f"'{name}' still has documents. Delete its documents first.")

    keys_updated = 0
    for key in list_keys(db):
        if name in key.allowed_collections:
            key.allowed_collections = [c for c in key.allowed_collections if c != name]  # a new list: JSON change
            keys_updated += 1
    db.delete(row)
    db.commit()
    STORES.pop(name, None)
    return CollectionDeleted(name=name, keys_updated=keys_updated)
