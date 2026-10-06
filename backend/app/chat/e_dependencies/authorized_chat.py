"""authorized_chat(): dependency: valid key + "chat:invoke" scope + this collection allowed and existing.
It runs BEFORE the route body, so a stream never starts for a refused call."""

from fastapi import Depends

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.check_collection import check_collection
from app.auth.e_dependencies.require_scope import require_scope
from app.chat.a_schemas.chat_request import ChatRequest
from app.core.h_stores.get_store import get_store


def authorized_chat(req: ChatRequest, principal: AppPrincipal = Depends(require_scope("chat:invoke"))) -> AppPrincipal:
    check_collection(principal, req.collection)
    get_store(req.collection)  # 404 collection_not_found now, not halfway through a stream
    return principal