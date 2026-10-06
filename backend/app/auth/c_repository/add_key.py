"""add_key(): saves a new api_keys row."""

from sqlalchemy.orm import Session

from app.auth.b_models.api_key import ApiKey

def add_key(db:Session, row:ApiKey) -> ApiKey:
    db.add(row)
    db.commit()
    return row