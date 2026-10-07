"""ping_database(): runs SELECT 1, the cheapest possible "are you there?"."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def ping_database(db: Session) -> None:
    db.execute(text("SELECT 1"))
