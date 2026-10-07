"""lifespan(): runs once at startup (before the first request) and once at shutdown."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.a_config.get_settings import get_settings
from app.core.b_logging.setup_logging import setup_logging
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.d_metrics.prune_request_logs import prune_request_logs
from app.core.h_stores.open_all_stores import open_all_stores
from app.documents.c_repository.fail_unfinished_jobs import fail_unfinished_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(get_settings().log_level)
    open_all_stores()
    with get_sessionmaker()() as db:
        fail_unfinished_jobs(db)
        prune_request_logs(db, get_settings().log_retention_days)
    yield
