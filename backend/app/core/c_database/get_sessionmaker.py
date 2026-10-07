"""get_sessionmaker(): the factory that opens database sessions on the shared engine."""

from functools import lru_cache

from sqlalchemy.orm import sessionmaker

from app.core.c_database.get_engine import get_engine


@lru_cache
def get_sessionmaker():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)

