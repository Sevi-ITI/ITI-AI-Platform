"""app_overviews(): every app the system knows (from its keys, its chats or a written profile), with
its profile and live counts: active keys, users, last request."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.app_overview import AppOverview
from app.admin.a_schemas.app_profile_in import AppProfileIn
from app.admin.c_repository.app_last_used import app_last_used
from app.admin.c_repository.app_user_counts import app_user_counts
from app.admin.c_repository.list_app_profiles import list_app_profiles
from app.auth.c_repository.list_keys import list_keys
from app.auth.d_keys.is_active import is_active


def app_overviews(db: Session) -> list[AppOverview]:
    profiles, users, last_used = list_app_profiles(db), app_user_counts(db), app_last_used(db)
    active_keys: dict[str, int] = {}
    for key in list_keys(db):
        active_keys[key.app_id] = active_keys.get(key.app_id, 0) + is_active(key.revoked_at, key.expires_at)
    overviews = []
    for app_id in sorted(set(profiles) | set(users) | set(active_keys)):
        profile = profiles.get(app_id)
        fields = AppProfileIn.model_validate(profile, from_attributes=True).model_dump() if profile else {}
        overviews.append(
            AppOverview(
                **fields,
                app_id=app_id,
                active_keys=active_keys.get(app_id, 0),
                users=users.get(app_id, 0),
                last_used_at=last_used.get(app_id),
                profile_updated_at=profile.updated_at if profile else None,
            )
        )
    return overviews
