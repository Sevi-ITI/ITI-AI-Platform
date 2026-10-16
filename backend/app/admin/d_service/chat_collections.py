"""chat_collections(): the collections a console person may ask, with their document counts and newest indexed
files. Lives in admin because it reads the documents feature (only admin may)."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.chat_collection import ChatCollection
from app.admin.c_repository.count_documents import count_documents
from app.admin.c_repository.list_documents_with_jobs import list_documents_with_jobs
from app.auth.a_schemas.app_principal import AppPrincipal

RECENT = 3


def chat_collections(db: Session, principal: AppPrincipal) -> list[ChatCollection]:
    counts = count_documents(db)
    out = []
    for name in sorted(principal.allowed_collections):
        recent: list[str] = []
        for document, job in list_documents_with_jobs(db, name, limit=20, offset=0):
            if job.status == "done" and document.filename not in recent:
                recent.append(document.filename)
            if len(recent) == RECENT:
                break
        out.append(ChatCollection(name=name, documents=counts.get(name, 0), recent_files=recent))
    return out
