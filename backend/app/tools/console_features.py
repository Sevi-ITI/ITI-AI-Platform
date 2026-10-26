"""console_features: the KILL SWITCHES for the console's "Tools & MCP" page (Phase 8.6d). One concern per file.

True  = the console shows that part and the API allows it (super admin only, every change logged).
False = the console hides it AND the API refuses it (404 feature_off), whatever a caller sends.
Change a value here, then restart uvicorn (and reload the console)."""

from collections.abc import Callable

from app.core.e_errors.app_error import AppError

CONSOLE_FEATURES = {
    "mcp_connections": True,  # add / edit / switch on and off / remove MCP servers (stdio: only servers in mcp_servers.py)
    "records_source": True,  # who answers the records questions: built-in or the records MCP server (no restart)
    "server_status": True,  # the status of every MCP server + a "test connection" button
    "tool_switches": True,  # each tool on or off
    "edit_descriptions": False,  # edit the text the model reads to pick a tool (a careless edit can break answers)
    "sql_tools": False,  # new tools written as one SELECT on the ai.* views (guarded, read-only login)
    "code_view": True,  # read a tool's code (tools.py section / SELECT / server schema), behind the security password
    "company_databases": True,  # each client company's database per system (direct or relay), on the Companies page
    "try_it": False,  # ask a question as a test employee ID with chosen tool scopes (reads REAL records; every use logged)
}


def feature_on(name: str) -> bool:
    return CONSOLE_FEATURES.get(name, False)


def require_feature(name: str) -> Callable[[], None]:
    """A FastAPI dependency: the route answers 404 feature_off while the switch is False."""

    def check() -> None:
        if not feature_on(name):
            raise AppError(404, "feature_off", f"'{name}' is switched off in app/tools/console_features.py.")

    return check
