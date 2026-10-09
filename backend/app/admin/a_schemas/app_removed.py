"""AppRemoved: what DELETE /v1/admin/apps/{app_id} removed (keep it as the record)."""

from pydantic import BaseModel


class AppRemoved(BaseModel):
    app_id: str
    keys_removed: int  # revoked / expired key rows deleted
    profile_removed: bool
