"""check_collection(): 403 collection_forbidden unless the calling app may read that collection."""

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.e_errors.app_error import AppError

def check_collection(principal: AppPrincipal, collection: str) -> None:
    if collection not in principal.allowed_collections:
        raise AppError(403, "collection_forbidden", f"This app cannot read '{collection}'.")
