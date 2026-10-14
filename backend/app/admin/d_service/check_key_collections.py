"""check_key_collections(): a key for one company may list only that company's collections, the ones shared with
it, and Global ones.
422 company_not_found (no such company); 422 unknown_collection; 422 collection_other_company."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.c_repository.list_collection_shares import list_collection_shares
from app.core.e_errors.app_error import AppError
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.company_row import CompanyRow


def check_key_collections(db: Session, company_id: str, collections: list[str]) -> None:
    if db.get(CompanyRow, company_id) is None:
        raise AppError(422, "company_not_found", f"No company named '{company_id}'.")
    owners = {name: company for name, company in db.execute(select(CollectionRow.name, CollectionRow.company_id))}
    shares = list_collection_shares(db)
    for name in collections:
        if name not in owners:
            raise AppError(422, "unknown_collection", f"No collection named '{name}'.")
        if owners[name] not in (None, company_id) and company_id not in shares.get(name, []):
            raise AppError(
                422,
                "collection_other_company",
                f"'{name}' belongs to the company '{owners[name]}' and isn't shared with '{company_id}'; "
                "a key for that company can't use it.",
            )
