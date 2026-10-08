"""document_rows(): uploaded file versions with their job status, for the admin Documents page."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.document_row import DocumentRow
from app.admin.c_repository.list_documents_with_jobs import list_documents_with_jobs


def document_rows(db: Session, collection: str | None, limit: int, offset: int) -> list[DocumentRow]:
    return [
        DocumentRow(
            document_id=doc.id,
            collection=doc.collection,
            filename=doc.filename,
            size_bytes=doc.size_bytes,
            uploaded_by=doc.uploaded_by,
            uploaded_by_user=doc.uploaded_by_user,
            created_at=doc.created_at,
            job_id=job.id,
            job_status=job.status,
            chunks=job.chunks,
            error=job.error,
            finished_at=job.finished_at,
        )
        for doc, job in list_documents_with_jobs(db, collection, limit, offset)
    ]
