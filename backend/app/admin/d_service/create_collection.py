"""create_collection(): adds a collection and opens it at once (no restart). 409 collection_exists if taken.
App keys are not given it automatically: grant it per key (PATCH /v1/admin/keys/{key_id})."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_create import CollectionCreate
from app.admin.a_schemas.collection_info import CollectionInfo
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_engine import get_engine
from app.core.e_errors.app_error import AppError
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.store_registry import STORES
from app.rag.d_vectorstore.open_store import open_store


def create_collection(db: Session, body: CollectionCreate, principal: AppPrincipal) -> CollectionInfo:
    db.add(CollectionRow(name=body.name, created_by=principal.console_user or principal.app_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "collection_exists", f"A collection named '{body.name}' already exists.") from None
    STORES[body.name] = open_store(get_engine(), body.name)
    return CollectionInfo(name=body.name, documents=0, chunks=0)
