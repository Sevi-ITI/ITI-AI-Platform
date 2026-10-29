"""UsageMonth: GET /v1/admin/usage. One calendar month in Manila time (D-8); starts_at and ends_at are its UTC bounds."""

from datetime import datetime

from pydantic import BaseModel

from app.admin.a_schemas.usage_company import UsageCompany


class UsageMonth(BaseModel):
    month: str
    starts_at: datetime
    ends_at: datetime
    companies: list[UsageCompany]
