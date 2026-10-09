"""CollectionDeleted: what DELETE /v1/admin/collections/{name} did."""

from pydantic import BaseModel


class CollectionDeleted(BaseModel):
    name: str
    keys_updated: int  # keys that listed the collection and no longer do
