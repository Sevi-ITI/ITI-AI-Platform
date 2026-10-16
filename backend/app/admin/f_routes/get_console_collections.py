"""GET /v1/console/collections: the collections the logged-in console person may ask (a tester: only theirs), for
the Chat page's picker and suggestion chips. Any console login; app keys are refused (they don't use the console).
In admin's URL table because it reads the documents feature."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.chat_collection import ChatCollection
from app.admin.d_service.chat_collections import chat_collections
from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.a_schemas.console_principal import ConsolePrincipal
from app.auth.e_dependencies.require_console_user import require_console_user
from app.auth.e_dependencies.require_scope import require_scope
from app.core.c_database.get_db import get_db


def get_console_collections(
    _: ConsolePrincipal = Depends(require_console_user),
    principal: AppPrincipal = Depends(require_scope("chat:invoke")),
    db: Session = Depends(get_db),
) -> list[ChatCollection]:
    return chat_collections(db, principal)
