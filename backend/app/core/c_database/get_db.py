"""get_db(): FastAPI dependency. `db: Session = Depends(get_db)` gives a route its own session,
closed automatically after the response."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.core.c_database.get_sessionmaker import get_sessionmaker


def get_db() -> Iterator[Session]:
    with get_sessionmaker()() as db:
        yield db
