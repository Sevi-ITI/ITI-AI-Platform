"""The Settings class: every ITI_* environment variable the service reads."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"  # a_config/ -> core/ -> app/ -> backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="ITI_", extra="ignore")

    # Database (Postgres + pgvector). Pool sized for ~10 requests at once, with room to spare.
    database_url: str = "postgresql+psycopg://iti:change-me@127.0.0.1:5432/iti_ai"
    db_pool_size: int = 10
    db_max_overflow: int = 10

    # Collections: names only; their chunks live in Postgres. A JSON list in .env.
    collections: list[str] = ["iti-docs"]

    # The model server. llm_parallel MUST equal OLLAMA_NUM_PARALLEL: how many answers are
    # generated at the same time. Extra requests wait in our queue, up to llm_queue_timeout_s.
    ollama_url: str = "http://127.0.0.1:11434"
    llm_parallel: int = 2
    llm_queue_timeout_s: float = 120.0

    upload_dir: str = "../data/uploads"
    max_upload_mb: int = 50
    log_level: str = "INFO"
    log_retention_days: int = 90  # request logs older than this are deleted at startup (RA 10173)

    # Records DB (Phase 8, SQL Server, read-only login iti_ai_reader). Empty = records tools off.
    # mssql+mssqlpython://iti_ai_reader:<password>@127.0.0.1:1433/iti_records?Encrypt=yes&TrustServerCertificate=yes
    records_db_url: str = ""
    # MCP servers are listed in app/tools/client/servers.py (Phase 8.6b); only their secrets live in .env.
