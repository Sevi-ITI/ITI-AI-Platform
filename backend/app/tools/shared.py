"""shared: what every part of app/tools uses. One concern per file (Phase 8.6c): everything shared is here.

- ToolSpec      what the model is told about one tool (name, description, argument schema, the key scope it needs)
- Tool          one built-in tool (tools.py): spec + argument model + the function that answers + its source title
- RECORDS_OF    the label on every per-employee result
- get_records_engine()  the ONE connection pool to the records DB (ITI_RECORDS_DB_URL, read-only login)
- read_secret()  a secret by its env-variable name: from the environment, else backend\\.env (never in tests)"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from dotenv import dotenv_values
from pydantic import BaseModel
from sqlalchemy import create_engine, event

from app.core.a_config.get_settings import get_settings
from app.core.a_config.settings import ENV_FILE

# --- ToolSpec -------------------------------------------------------------------------------------------------


class ToolSpec(BaseModel):
    """What the model sees. The asking employee is never one of the arguments: run_tool adds it from ITI-User-Id."""

    name: str
    description: str
    parameters: dict  # JSON schema of the arguments, in Ollama's "tools" format
    scope: str  # the key scope needed to be offered this tool, e.g. "records:read"

    def as_ollama(self) -> dict:
        function = {"name": self.name, "description": self.description, "parameters": self.parameters}
        return {"type": "function", "function": function}


# --- Tool -----------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Tool:
    """One built-in tool (tools.py).
    - args: the pydantic model that checks the model's arguments (extra fields refused: no employee_id)
    - run(conn, employee_id, args) -> dict: the answer, from fixed queries only
    - describe(result) -> (source title, holds data): "Records: payslip 2026-09-30", never values
    - topic: a few words for the system prompt ("leave credits"); source: the system that answers ("records")"""

    spec: ToolSpec
    args: type[BaseModel]
    run: Callable[..., dict]
    describe: Callable[[dict], tuple[str, bool]]
    topic: str
    source: str = "records"


# --- RECORDS_OF -----------------------------------------------------------------------------------------------

# The 8.1 spike showed why: without this label the model presented the asker's own leave credits as "Juan's".
RECORDS_OF = "the logged-in employee (YOU), nobody else"


# --- the records DB -------------------------------------------------------------------------------------------

CONNECT_TIMEOUT_S = 5  # a records DB that is down can't hold a chat (the driver's default is about 15 s)
QUERY_TIMEOUT_S = 10  # and a slow query is cut off


@lru_cache
def get_records_engine():
    """The ONE connection pool to the records DB, made on first use (built-in tools and the records MCP server)."""
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


# --- secrets --------------------------------------------------------------------------------------------------


def read_secret(name: str) -> str:
    """e.g. read_secret("ITI_MCP_PAYROLL_TOKEN"). "" when not set. Secrets live only in .env, never in a committed file."""
    if os.environ.get(name):
        return os.environ[name]
    if os.environ.get("ITI_IGNORE_ENV_FILE") or not ENV_FILE.exists():
        return ""
    return dotenv_values(ENV_FILE).get(name) or ""
