"""store: the Tools & MCP settings the console changes, kept in Postgres (Phase 8.6d). One concern per file: the
tables and every read and write of them are here. Secrets are NEVER stored: a connection keeps only the NAME of
the backend\\.env variable that holds its secret.

Tables: tools_settings (records_source, ...), mcp_connections (the servers the AI host connects to; filled once
from servers.py, then managed in the console), tool_overrides (a tool switched off / its description changed),
sql_tools (tools written as SQL in the console; tool_overrides also keeps
which tools from other machines were approved), tools_changes (who changed what, when, old and new value).
Every read opens a short session: a few small queries per chat question, no cache to go stale."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.a_config.get_settings import get_settings
from app.core.c_database.base import Base
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.c_database.utcnow import utcnow
from app.tools.servers import MCP_SERVERS

# --- tables ---------------------------------------------------------------------------------------------------


class ToolsSetting(Base):
    __tablename__ = "tools_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "records_source"
    value: Mapped[str] = mapped_column(Text)


class McpConnection(Base):
    __tablename__ = "mcp_connections"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)  # tool names become "<name>__<tool>"
    transport: Mapped[str] = mapped_column(String(8))  # stdio | http
    server: Mapped[str | None] = mapped_column(String(64))  # stdio: a server defined in mcp_servers.py
    url: Mapped[str | None] = mapped_column(String(300))  # http
    token_env: Mapped[str | None] = mapped_column(String(64))  # http: the .env variable with the secret (not the secret)
    scope: Mapped[str] = mapped_column(String(64))
    topics: Mapped[list] = mapped_column(JSON)
    records: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_by: Mapped[str] = mapped_column(String(64))


class ToolOverride(Base):
    __tablename__ = "tool_overrides"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)  # a built-in, SQL or "<server>__<tool>" name
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)  # None = the description from the code / server
    approved: Mapped[str | None] = mapped_column(String(64))  # http MCP tools: the ToolSpec.fingerprint approved
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_by: Mapped[str] = mapped_column(String(64))


class SqlTool(Base):
    __tablename__ = "sql_tools"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str] = mapped_column(Text)
    sql: Mapped[str] = mapped_column(Text)  # checked by sql_tools.check_sql_tool before it is saved
    parameters: Mapped[list] = mapped_column(JSON)  # [{"name", "type": string|integer|date, "description", "required"}]
    scope: Mapped[str] = mapped_column(String(64))
    topic: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_by: Mapped[str] = mapped_column(String(64))


class ToolsChange(Base):
    __tablename__ = "tools_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    who: Mapped[str] = mapped_column(String(64))  # the console username, or "key:<key_id>"
    what: Mapped[str] = mapped_column(String(40))  # e.g. "connection.save", "tool.switch", "records_source"
    target: Mapped[str] = mapped_column(String(100))
    old: Mapped[dict | None] = mapped_column(JSON)
    new: Mapped[dict | None] = mapped_column(JSON)


CONNECTION_FIELDS = ("name", "transport", "server", "url", "token_env", "scope", "topics", "records", "enabled")
SQL_TOOL_FIELDS = ("name", "description", "sql", "parameters", "scope", "topic", "enabled")


def _as_dict(row, fields) -> dict:
    return {field: getattr(row, field) for field in fields}


def log_change(db, who: str, what: str, target: str, old: dict | None, new: dict | None) -> None:
    db.add(ToolsChange(who=who, what=what, target=target, old=old, new=new))


# --- settings -------------------------------------------------------------------------------------------------


def _setting(name: str) -> str | None:
    with get_sessionmaker()() as db:
        row = db.get(ToolsSetting, name)
        return row.value if row else None


def records_source() -> str:
    """builtin | mcp: the console's choice, else ITI_RECORDS_SOURCE in backend\\.env (default builtin)."""
    return _setting("records_source") or get_settings().records_source


def set_records_source(value: str, who: str) -> None:
    with get_sessionmaker()() as db:
        old = records_source()
        row = db.get(ToolsSetting, "records_source") or ToolsSetting(key="records_source", value=value)
        row.value = value
        db.add(row)
        log_change(db, who, "records_source", "records_source", {"value": old}, {"value": value})
        db.commit()


# --- MCP connections ------------------------------------------------------------------------------------------


def connection_entries() -> list[dict]:
    """Every connection as a servers.py-style entry. The first call fills the table from servers.py (once)."""
    with get_sessionmaker()() as db:
        if db.get(ToolsSetting, "connections_seeded") is None:
            for entry in MCP_SERVERS:
                db.merge(McpConnection(**{f: entry.get(f) for f in CONNECTION_FIELDS}, updated_by="servers.py"))
            db.add(ToolsSetting(key="connections_seeded", value=utcnow().isoformat()))
            db.commit()
        rows = db.scalars(select(McpConnection).order_by(McpConnection.name)).all()
        return [{k: v for k, v in _as_dict(row, CONNECTION_FIELDS).items() if v is not None} for row in rows]


def save_connection(entry: dict, who: str) -> None:
    """Adds or replaces one connection (already checked by the caller)."""
    connection_entries()  # make sure the starting set is in before the first change
    with get_sessionmaker()() as db:
        row = db.get(McpConnection, entry["name"])
        old = _as_dict(row, CONNECTION_FIELDS) if row else None
        db.merge(McpConnection(**{f: entry.get(f) for f in CONNECTION_FIELDS}, updated_at=utcnow(), updated_by=who))
        log_change(db, who, "connection.save", entry["name"], old, {f: entry.get(f) for f in CONNECTION_FIELDS})
        db.commit()


def delete_connection(name: str, who: str) -> bool:
    connection_entries()
    with get_sessionmaker()() as db:
        row = db.get(McpConnection, name)
        if row is None:
            return False
        log_change(db, who, "connection.delete", name, _as_dict(row, CONNECTION_FIELDS), None)
        db.delete(row)
        db.commit()
        return True


# --- tool overrides -------------------------------------------------------------------------------------------


def tool_overrides() -> dict[str, dict]:
    """{tool name: {"enabled", "description", "approved"}} for every tool changed or approved in the console."""
    with get_sessionmaker()() as db:
        rows = db.scalars(select(ToolOverride)).all()
        return {row.name: {"enabled": row.enabled, "description": row.description, "approved": row.approved} for row in rows}


def save_tool_override(name: str, enabled: bool, description: str | None, who: str, what: str) -> None:
    with get_sessionmaker()() as db:
        row = db.get(ToolOverride, name)
        old = {"enabled": row.enabled, "description": row.description} if row else None
        approved = row.approved if row else None
        if enabled and description is None and approved is None:
            if row:
                db.delete(row)  # back to the code's defaults: no override left
        else:
            db.merge(ToolOverride(name=name, enabled=enabled, description=description, approved=approved, updated_at=utcnow(), updated_by=who))
        log_change(db, who, what, name, old, {"enabled": enabled, "description": description})
        db.commit()


def approve_tool(name: str, fingerprint: str, who: str) -> None:
    """A super admin approved a tool from another machine as it is now (its text and arguments)."""
    with get_sessionmaker()() as db:
        row = db.get(ToolOverride, name) or ToolOverride(name=name, enabled=True, updated_by=who)
        old = {"approved": row.approved}
        row.approved, row.updated_at, row.updated_by = fingerprint, utcnow(), who
        db.add(row)
        log_change(db, who, "tool.approve", name, old, {"approved": fingerprint})
        db.commit()


# --- SQL tools ------------------------------------------------------------------------------------------------


def sql_tool_rows() -> list[dict]:
    with get_sessionmaker()() as db:
        return [_as_dict(row, SQL_TOOL_FIELDS) for row in db.scalars(select(SqlTool).order_by(SqlTool.name)).all()]


def save_sql_tool(entry: dict, who: str) -> None:
    """Adds or replaces one SQL tool (already checked by sql_tools.check_sql_tool)."""
    with get_sessionmaker()() as db:
        row = db.get(SqlTool, entry["name"])
        old = _as_dict(row, SQL_TOOL_FIELDS) if row else None
        db.merge(SqlTool(**{f: entry[f] for f in SQL_TOOL_FIELDS}, updated_at=utcnow(), updated_by=who))
        log_change(db, who, "sql_tool.save", entry["name"], old, {f: entry[f] for f in SQL_TOOL_FIELDS})
        db.commit()


def delete_sql_tool(name: str, who: str) -> bool:
    with get_sessionmaker()() as db:
        row = db.get(SqlTool, name)
        if row is None:
            return False
        log_change(db, who, "sql_tool.delete", name, _as_dict(row, SQL_TOOL_FIELDS), None)
        db.delete(row)
        db.execute(delete(ToolOverride).where(ToolOverride.name == name))
        db.commit()
        return True


# --- Try it ---------------------------------------------------------------------------------------------------


def log_try(who: str, test_user_id: str, scopes: list[str], tools: list[str], outcome: str) -> None:
    """One row per use of the console's Try it: who, as which test ID, with which scopes, which tools ran, how it
    ended. Never the question, the arguments or the answer (they can hold personal data)."""
    with get_sessionmaker()() as db:
        log_change(db, who, "try_it", f"user:{test_user_id}"[:100], None, {"scopes": scopes, "tools": tools, "outcome": outcome})
        db.commit()


# --- the change log -------------------------------------------------------------------------------------------


def recent_changes(limit: int = 100) -> list[dict]:
    with get_sessionmaker()() as db:
        rows = db.scalars(select(ToolsChange).order_by(ToolsChange.id.desc()).limit(limit)).all()
        return [{"at": row.at, "who": row.who, "what": row.what, "target": row.target, "old": row.old, "new": row.new} for row in rows]
