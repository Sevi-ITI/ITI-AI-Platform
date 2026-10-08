"""AppOverview: one connected system for the Apps & keys page: its profile (if any) plus live counts."""

from app.admin.a_schemas.app_profile_in import AppProfileIn
from app.core.f_types.utc_datetime import UtcDateTime


class AppOverview(AppProfileIn):
    app_id: str
    active_keys: int  # not revoked and not expired
    users: int  # distinct ITI-User-Id values that have chatted
    last_used_at: UtcDateTime | None  # the app's latest request in the request log
    profile_updated_at: UtcDateTime | None  # None = no profile written yet
