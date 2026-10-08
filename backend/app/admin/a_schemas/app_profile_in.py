"""AppProfileIn: the body of PUT /v1/admin/apps/{app_id}. Every field optional; the whole profile is
replaced (a field left out becomes empty)."""

from pydantic import BaseModel, Field


class AppProfileIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    company: str | None = Field(default=None, max_length=100)
    owner_name: str | None = Field(default=None, max_length=100)
    owner_email: str | None = Field(default=None, max_length=200, pattern=r"^[^@\s]+@[^@\s]+$")
    notes: str | None = Field(default=None, max_length=2000)
