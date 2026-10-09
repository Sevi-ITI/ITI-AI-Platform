"""move_collection(): gives a collection to another company, or makes it Global (company_id None).
404 collection_not_found; 422 company_not_found; 409 collection_in_use when an active key of a different company
still lists it (it would reach another company's documents: take it off that key first). Making it Global never
conflicts: Global collections may be given to any company's key."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.d_service.collection_infos import collection_infos
from app.auth.c_repository.list_keys import list_keys
from app.auth.d_keys.is_active import is_active
from app.core.e_errors.app_error import AppError
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.company_row import CompanyRow


def move_collection(db: Session, name: str, company_id: str | None) -> CollectionInfo:
    row = db.get(CollectionRow, name)
    if row is None:
        raise AppError(404, "collection_not_found", f"No collection named '{name}'.")
    if company_id is not None:
        if db.get(CompanyRow, company_id) is None:
            raise AppError(422, "company_not_found", f"No company named '{company_id}'.")
        for key in list_keys(db):
            if name in key.allowed_collections and key.company_id != company_id and is_active(
                key.revoked_at, key.expires_at
            ):
                raise AppError(
                    409,
                    "collection_in_use",
                    f"Key {key.key_id} ({key.app_id}, company '{key.company_id}') still uses '{name}'. "
                    "Take it off that key first.",
                )
    row.company_id = company_id
    db.commit()
    return next(c for c in collection_infos(db) if c.name == name)
