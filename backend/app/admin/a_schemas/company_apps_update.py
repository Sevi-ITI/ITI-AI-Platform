"""CompanyAppsUpdate: the body of PUT /v1/admin/companies/{company_id}/apps: the whole list of apps linked to the
company (their keys may then be made for it). [] = linked to no app."""

from pydantic import BaseModel


class CompanyAppsUpdate(BaseModel):
    app_ids: list[str]
