"""get_engine(): the ONE database connection pool for this process, made on first use.
pool_size + max_overflow = how many requests can hold a database session at the same time."""

from functools import lru_cache

from sqlalchemy import create_engine

from app.core.a_config.get_settings import get_settings


@lru_cache()
def get_engine():
    s = get_settings()
    return create_engine(s.database_url, pool_pre_ping=True, pool_size=s.db_pool_size, max_overflow=s.db_max_overflow)
