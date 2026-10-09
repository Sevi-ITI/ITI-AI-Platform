"""company_infos(): every company with the collections it owns and its active keys (any app)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.a_schemas.company_info import CompanyInfo
from app.auth.c_repository.list_keys import list_keys
from app.auth.d_keys.is_active import is_active
from app.core.h_stores.collection_row import CollectionRow
from app.core.h_stores.company_row import CompanyRow


def company_infos(db: Session) -> list[CompanyInfo]:
    owned: dict[str, list[str]] = {}
    for name, company_id in db.execute(select(CollectionRow.name, CollectionRow.company_id).order_by(CollectionRow.name)):
        if company_id is not None:
            owned.setdefault(company_id, []).append(name)
    active: dict[str, int] = {}
    for key in list_keys(db):
        active[key.company_id] = active.get(key.company_id, 0) + is_active(key.revoked_at, key.expires_at)
    return [
        CompanyInfo(
            company_id=c.company_id,
            name=c.name,
            notes=c.notes,
            created_at=c.created_at,
            collections=owned.get(c.company_id, []),
            active_keys=active.get(c.company_id, 0),
        )
        for c in db.scalars(select(CompanyRow).order_by(CompanyRow.name))
    ]
