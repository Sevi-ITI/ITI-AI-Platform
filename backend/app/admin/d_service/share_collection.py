"""share_collection(): sets the companies (besides the owner) a collection is shared with; their keys may then be
given it. 404 collection_not_found; 409 collection_global (Global collections are open to every company already);
422 company_not_found; 409 collection_in_use when a company taken off the list still has an active key that uses it
(take it off that key first). The owner, if listed, is ignored."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.c_repository.list_collection_shares import list_collection_shares
from app.admin.d_service.collection_infos import collection_infos
from app.auth.c_repository.list_keys import list_keys
from app.auth.d_keys.is_active import is_active
from app.core.e_errors.app_error import AppError
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.collection_share_row import CollectionShareRow
from app.core.h_stores.company_row import CompanyRow


def share_collection(db: Session, name: str, company_ids: list[str]) -> CollectionInfo:
    row = db.get(CollectionRow, name)
    if row is None:
        raise AppError(404, "collection_not_found", f"No collection named '{name}'.")
    if row.company_id is None:
        raise AppError(409, "collection_global", f"'{name}' is Global: every company's key may be given it already.")
    wanted = sorted(set(company_ids) - {row.company_id})
    for company_id in wanted:
        if db.get(CompanyRow, company_id) is None:
            raise AppError(422, "company_not_found", f"No company named '{company_id}'.")

    removed = set(list_collection_shares(db).get(name, [])) - set(wanted)
    for key in list_keys(db):
        if key.company_id in removed and name in key.allowed_collections and is_active(key.revoked_at, key.expires_at):
            raise AppError(
                409,
                "collection_in_use",
                f"Key {key.key_id} ({key.app_id}, company '{key.company_id}') still uses '{name}'. "
                "Take it off that key first.",
            )

    db.execute(delete(CollectionShareRow).where(CollectionShareRow.collection == name))
    db.add_all(CollectionShareRow(collection=name, company_id=c) for c in wanted)
    db.commit()
    return next(c for c in collection_infos(db) if c.name == name)
