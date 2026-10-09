"""CollectionInfo: one collection: uploaded file versions and chunks currently searchable. in_settings = listed in
ITI_COLLECTIONS (re-created at every startup, so the console can't delete it)."""

from pydantic import BaseModel


class CollectionInfo(BaseModel):
    name: str
    documents: int
    chunks: int
    in_settings: bool = False
