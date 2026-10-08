"""CollectionCreate: a new collection's name: lowercase letters, digits and hyphens, 2-64 characters."""

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")  # e.g. "finance-docs"
