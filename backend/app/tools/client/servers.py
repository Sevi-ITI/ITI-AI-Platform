"""MCP_SERVERS: the MCP servers the AI host connects to (connection: AI host -> MCP server).

A server is used only when "enabled" is True AND its secret is set in backend\\.env under "token_env".
Secrets never go in this file. Every entry is checked by the tests (app/tests/test_mcp_tools.py).

Add a server: copy the EXAMPLE entry below into MCP_SERVERS, change it, then put its secret in backend\\.env:
    ITI_MCP_<NAME>_TOKEN=<long random secret, letters and digits>
The server itself checks the same secret (see app/tools/server/README.md).

Fields: name      tool names become "<name>__<tool>"; lowercase, digits, "_"
        url       http only for 127.0.0.1 / localhost; any other host must be https
        scope     the key scope needed to be offered this server's tools, e.g. "records:read"
        token_env the environment variable (in backend\\.env) that holds the shared secret
        topics    a few words per kind of question it answers, for the system prompt
        enabled   False = listed but not used"""

MCP_SERVERS = [
    {
        "name": "records",
        "url": "http://127.0.0.1:8100/mcp",
        "scope": "records:read",
        "token_env": "ITI_MCP_RECORDS_TOKEN",
        "topics": ["leave credits", "absences / attendance", "payslip deductions"],
        # Decision D6: the built-in records tools are the default. True = also use the records MCP server
        # (start it first: python -m app.tools.server.records_server).
        "enabled": False,
    },
]

# EXAMPLE (copy into MCP_SERVERS above):
#   {
#       "name": "tickets",
#       "url": "https://tickets-mcp.iti.local/mcp",
#       "scope": "tickets:read",          # also add it to Scope in app/admin/a_schemas/key_create.py
#       "token_env": "ITI_MCP_TICKETS_TOKEN",
#       "topics": ["IT support tickets"],
#       "enabled": True,
#   },
