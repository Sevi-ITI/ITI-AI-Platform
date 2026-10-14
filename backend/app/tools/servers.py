"""servers: ALL connections from the AI host to MCP servers. One concern per file (Phase 8.6c): to connect a new
server, add one entry to MCP_SERVERS below (copy an EXAMPLE). No secrets here: they live only in backend\\.env.

Two ways to connect:
- "stdio": a server that runs on THIS machine and lives in app/tools/mcp_servers.py. The AI host starts it itself
  when it needs it: no extra window, no port, no secret (only the host that started it can talk to it).
- "http":  a server somewhere else (e.g. a C# payroll MCP server). Needs a url (https unless 127.0.0.1 / localhost)
  and a shared secret in backend\\.env under "token_env".

Fields: name       tool names become "<name>__<tool>"; lowercase, digits, "_"
        transport  "stdio" or "http"
        server     stdio only: the server's name in app/tools/mcp_servers.py (SERVERS)
        url        http only, e.g. "https://payroll-mcp.iti.local/mcp"
        token_env  http only: the env variable in backend\\.env that holds the shared secret, e.g. "ITI_MCP_PAYROLL_TOKEN"
        scope      the key scope needed to be offered this server's tools, e.g. "records:read"
        topics     a few words per kind of question it answers, for the system prompt
        records    True = it answers the records questions: used only when ITI_RECORDS_SOURCE=mcp (see below)
        enabled    False = listed but not used

ITI_RECORDS_SOURCE in backend\\.env decides who answers the records questions (decision D6):
    builtin (default)  the built-in tools (app/tools/tools.py) read the records DB directly
    mcp                the "records": True server below answers them instead (restart uvicorn after a change)"""

MCP_SERVERS = [
    {
        "name": "records",
        "transport": "stdio",
        "server": "records",
        "scope": "records:read",
        "topics": ["leave credits", "absences / attendance", "payslip deductions"],
        "records": True,
        "enabled": True,
    },
]

# EXAMPLE, a server on another machine (copy into MCP_SERVERS above, then put the secret in backend\.env):
#   {
#       "name": "tickets",
#       "transport": "http",
#       "url": "https://tickets-mcp.iti.local/mcp",
#       "token_env": "ITI_MCP_TICKETS_TOKEN",
#       "scope": "tickets:read",          # also add it to Scope in app/admin/a_schemas/key_create.py
#       "topics": ["IT support tickets"],
#       "enabled": True,
#   },
#
# EXAMPLE, a second server on this machine (add its section to app/tools/mcp_servers.py first):
#   {"name": "overtime", "transport": "stdio", "server": "overtime", "scope": "records:read",
#    "topics": ["overtime"], "enabled": True},
