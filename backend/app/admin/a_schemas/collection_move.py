"""CollectionMove: the body of PATCH /v1/admin/collections/{name}: the new owning company, or null for Global."""

from pydantic import BaseModel


class CollectionMove(BaseModel):
    company_id: str | None
