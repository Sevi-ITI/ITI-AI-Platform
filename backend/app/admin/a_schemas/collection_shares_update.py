"""CollectionSharesUpdate: the body of PUT /v1/admin/collections/{name}/shares: the whole list of companies (besides
the owner) whose keys may also be given the collection. [] = shared with no one."""

from pydantic import BaseModel


class CollectionSharesUpdate(BaseModel):
    company_ids: list[str]
