"""usage_for_month(): one month of the usage ledger as company -> key rows, with totals per company (billing step 4a).
Companies are sorted by id; Global (company None) comes last."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.a_schemas.usage_company import UsageCompany
from app.admin.a_schemas.usage_key_row import UsageKeyRow
from app.admin.a_schemas.usage_month import UsageMonth
from app.admin.a_schemas.usage_totals import UsageTotals
from app.admin.c_repository.usage_by_key import usage_by_key
from app.admin.d_service.manila_month import manila_month
from app.core.h_stores.company_row import CompanyRow

FIELDS = list(UsageTotals.model_fields)

def usage_for_month(db: Session, month: str | None) -> UsageMonth:
    label, starts, ends = manila_month(month)
    names = dict(db.execute(select(CompanyRow.company_id, CompanyRow.name)).all())
    keys_of: dict[str | None, list[UsageKeyRow]] = {}
    for row in usage_by_key(db, starts, ends):
        totals = UsageTotals(**{name: row[name] for name in FIELDS})
        keys_of.setdefault(row["company_id"], []).append(UsageKeyRow(app_id=row["app_id"], key_id=row["key_id"], totals=totals))
    companies = [
        UsageCompany(
            company_id=company_id,
            name=names.get(company_id),
            totals=UsageTotals(**{name: sum(getattr(key.totals, name) for key in keys) for name in FIELDS}),
            keys=sorted(keys, key=lambda key: (key.app_id or "", key.key_id or "")),
        )
        for company_id, keys in sorted(keys_of.items(), key=lambda item: (item[0] is None, item[0] or ""))
    ]
    return UsageMonth(month=label, starts_at=starts, ends_at=ends, companies=companies)
