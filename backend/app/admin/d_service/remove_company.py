"""remove_company(): deletes a company that owns nothing: no collections and no key rows (any state).
404 company_not_found; 409 company_iti (ITI itself); 409 company_in_use."""

from sqlalchemy.orm import Session

from app.auth.c_repository.list_keys import list_keys
from app.core.e_errors.app_error import AppError
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.company_row import CompanyRow
from app.core.h_stores.iti_company import ITI_COMPANY_ID


def remove_company(db: Session, company_id: str) -> None:
    if company_id == ITI_COMPANY_ID:
        raise AppError(409, "company_iti", "ITI's own company can't be removed.")
    row = db.get(CompanyRow, company_id)
    if row is None:
        raise AppError(404, "company_not_found", f"No company named '{company_id}'.")
    owns = db.query(CollectionRow).filter(CollectionRow.company_id == company_id).count()
    keys = sum(1 for k in list_keys(db) if k.company_id == company_id)
    if owns or keys:
        raise AppError(
            409,
            "company_in_use",
            f"'{company_id}' still has {owns} collection(s) and {keys} key(s): delete or move them first.",
        )
    db.delete(row)
    db.commit()
