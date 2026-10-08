"""POST /v1/console/login: username + password -> a session pass (8 h)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.console.a_schemas.login_request import LoginRequest
from app.console.a_schemas.login_result import LoginResult
from app.console.d_service.log_in import log_in
from app.core.c_database.get_db import get_db


def post_login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResult:
    return log_in(db, body)
