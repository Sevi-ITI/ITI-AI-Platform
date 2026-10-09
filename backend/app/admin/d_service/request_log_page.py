"""request_log_page(): a page of the request log for the admin Requests view."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.request_log_out import RequestLogOut
from app.admin.c_repository.list_request_logs import list_request_logs


def request_log_page(
    db: Session,
    app_id: str | None,
    user_id: str | None,
    errors_only: bool,
    limit: int,
    offset: int,
    company_id: str | None = None,
) -> list[RequestLogOut]:
    rows = list_request_logs(db, app_id, user_id, errors_only, limit, offset, company_id)
    return [RequestLogOut.model_validate(r, from_attributes=True) for r in rows]
