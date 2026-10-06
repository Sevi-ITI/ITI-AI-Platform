"""require_app(): dependency for routes called by ITI's apps. Reads the ITI-Api-Key header.
Declaring the header with APIKeyHeader also adds the "Authorize" button to /docs."""

from fastapi import Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.principal_from_key import principal_from_key
from app.core.c_database.get_db import get_db

API_KEY_HEADER = APIKeyHeader(name="ITI-Api-Key", auto_error=False)  # auto_error=False: we raise our own shape

def require_app(key: str | None = Depends(API_KEY_HEADER), db: Session = Depends(get_db)) -> AppPrincipal:
    return principal_from_key(key, db)
