"""remove_company(): deletes a company that owns no collection and has no key that still works. Its revoked keys
are deleted with it (Vince, 2026-10-22: a test company must be removable); the request log keeps their key_id as
plain text, so history stays readable. Collections shared with it are un-shared; its app links and its company
databases (ON DELETE CASCADE) go too. Its users' chats are kept, like a disconnected app's.
404 company_not_found; 409 company_iti (ITI itself); 409 company_in_use."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.admin.b_models.app_company import AppCompany
from app.auth.b_models.api_key import ApiKey
from app.auth.c_repository.list_keys import list_keys
from app.core.e_errors.app_error import AppError
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.collection_share_row import CollectionShareRow
from app.core.h_stores.company_row import CompanyRow
from app.core.h_stores.iti_company import ITI_COMPANY_ID


def remove_company(db: Session, company_id: str) -> None:
    if company_id == ITI_COMPANY_ID:
        raise AppError(409, "company_iti", "ITI's own company can't be removed.")
    row = db.get(CompanyRow, company_id)
    if row is None:
        raise AppError(404, "company_not_found", f"No company named '{company_id}'.")
    owns = db.query(CollectionRow).filter(CollectionRow.company_id == company_id).count()
    live_keys = sum(1 for k in list_keys(db) if k.company_id == company_id and k.revoked_at is None)
    if owns or live_keys:
        raise AppError(
            409,
            "company_in_use",
            f"'{company_id}' still has {owns} collection(s) and {live_keys} key(s) not revoked: "
            "delete or move the collections and revoke the keys first.",
        )
    db.execute(delete(ApiKey).where(ApiKey.company_id == company_id))  # only revoked ones are left
    db.execute(delete(CollectionShareRow).where(CollectionShareRow.company_id == company_id))
    db.execute(delete(AppCompany).where(AppCompany.company_id == company_id))
    db.delete(row)
    db.commit()
