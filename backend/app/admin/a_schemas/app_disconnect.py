"""AppDisconnect: the body of POST /v1/admin/apps/{app_id}/disconnect."""

from pydantic import BaseModel


class AppDisconnect(BaseModel):
    erase_chats: bool = False  # also delete every conversation of every user of this app (RA 10173, app retired)
