"""CollectionInfo: one collection: uploaded file versions and chunks currently searchable."""

from pydantic import BaseModel


class CollectionInfo(BaseModel):
    name: str
    documents: int
    chunks: int
