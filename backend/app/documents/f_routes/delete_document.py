"""DELETE /v1/documents?collection=iti-docs&filename=Old Policy.pdf: an app removes a file completely (204).
Needs documents:write and access to the collection; the same rules as the admin delete (file name only,
409 while it is being indexed, 404 if there is no such file). Supervisors in the console may not delete."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.check_can_change_existing import check_can_change_existing
from app.auth.e_dependencies.check_collection import check_collection
from app.auth.e_dependencies.require_scope import require_scope
from app.core.c_database.get_db import get_db
from app.documents.d_service.remove_document import remove_document


def delete_document(
    collection: str,
    filename: str,
    principal: AppPrincipal = Depends(require_scope("documents:write")),
    db: Session = Depends(get_db),
) -> None:
    check_collection(principal, collection)
    check_can_change_existing(principal)
    remove_document(db, collection, filename)
