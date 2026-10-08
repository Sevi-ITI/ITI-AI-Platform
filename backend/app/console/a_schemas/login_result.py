"""LoginResult: what a successful login returns. The console's server keeps `session` in an httpOnly
cookie and sends it to FastAPI as the ITI-Console-Session header; the browser's scripts never see it."""

from pydantic import BaseModel

from app.console.a_schemas.account_info import AccountInfo
from app.core.f_types.utc_datetime import UtcDateTime


class LoginResult(BaseModel):
    session: str  # iti_cs_...  shown only here, once
    expires_at: UtcDateTime
    account: AccountInfo
