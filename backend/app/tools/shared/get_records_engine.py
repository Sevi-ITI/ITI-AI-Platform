"""get_records_engine(): the ONE connection pool to the records DB (ITI_RECORDS_DB_URL, read-only login
iti_ai_reader), made on first use. Used by the built-in tools and by the records MCP server.
A records DB that is down or slow can't hold a chat: logging in gives up after CONNECT_TIMEOUT_S seconds
(the driver's default is about 15) and every query is cut off after QUERY_TIMEOUT_S."""

from functools import lru_cache

from sqlalchemy import create_engine, event

from app.core.a_config.get_settings import get_settings

CONNECT_TIMEOUT_S = 5
QUERY_TIMEOUT_S = 10


@lru_cache
def get_records_engine():
    engine = create_engine(
        get_settings().records_db_url,
        connect_args={"timeout": CONNECT_TIMEOUT_S},  # mssql-python: login timeout
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )

    @event.listens_for(engine, "connect")
    def set_query_timeout(dbapi_connection, _record):
        dbapi_connection.timeout = QUERY_TIMEOUT_S  # mssql-python: per-query timeout

    return engine
