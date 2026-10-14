# Tools (Phase 8): what the chatbot can look up, and how it connects

The chatbot answers from company documents (RAG) and, for keys with the right scope, from **tools**: small,
read-only lookups such as "the asking employee's leave credits". This folder holds everything about tools,
by role. Routes (the API) are listed in `app/ROUTES.md`.

```
app/tools/
├── catalog/   THE TOOLS. One file per tool + registry.py           → change or add a tool here
├── client/    AI host → MCP servers. servers.py lists them         → add or change a connection here
├── server/    MCP servers (+ their connection to an app or DB)     → a new system's server goes here
├── host/      the machinery: offer tools, the model loop, run a call (rarely changed)
└── shared/    used by all: ToolSpec, Tool, the records DB engine, RECORDS_OF, read_secret
```

## How a question flows

```
C# app ──/v1/chat──▶ chat ──▶ host/answer_with_tools ──▶ the model sees: catalog tools + MCP tools + "documents"
                                     │                       ├─ documents / no tool ─▶ RAG (unchanged)
                                     │                       └─ a tool call ─▶ host/run_tool
                                     │                                          ├─ catalog tool ─▶ fixed SQL on ai.* views
                                     │                                          └─ "<server>__<tool>" ─▶ client ─▶ MCP server ─▶ its app / DB
                                     └─ employee_id ALWAYS from ITI-User-Id (never from the model)
```

## Common changes

| I want to... | Do this |
|---|---|
| **Change a tool** (its question, query, description) | Open `catalog/<tool>.py`. Everything about the tool is in that one file |
| **Add a tool** on the records DB | Copy `catalog/_new_tool.py.example` → `catalog/<name>.py`, fill it in, add one line to `catalog/registry.py`. It works built-in **and** over the records MCP server |
| **Connect the AI host to an MCP server** | Add an entry to `MCP_SERVERS` in `client/servers.py` (copy the EXAMPLE there), put its secret in `backend\.env` under its `token_env` |
| **Switch an MCP server off** | `"enabled": False` in `client/servers.py`, or remove its secret from `.env` |
| **Add an MCP server for a new system** | Copy `server/_new_server.py.example` → `server/<name>_server.py`; its connection to the app/DB is at the top of the file; then the `client/servers.py` entry above |
| **Give an app access to tools** | Its key needs the tool's scope (`records:read`): console → Apps & keys → preset "Chat + own records" |
| **A new kind of access** (e.g. `tickets:read`) | Add the scope to `Scope` in `app/admin/a_schemas/key_create.py` (+ a console preset) |

After any change: `ruff check .`, `pytest -q` (from `backend\`), restart uvicorn; for tools the live check
`python -m scripts.check_records_chat`. `app/tests/test_templates.py` keeps the `.example` templates working.

## Rules every tool and server follows

1. **The model never chooses whose data is read.** No `employee_id` in what the model sees; the host fills it in
   from `ITI-User-Id` (catalog: `run(conn, employee_id, args)`; MCP: removed from the schema, overwritten on every call).
2. **Read-only, fixed queries:** bound parameters, `WHERE employee_id = :employee_id`, views in schema `ai` only.
3. **Every tool has a scope**, checked twice: when offering it (`tools_for`) and when running it (`run_tool`).
4. **Results never go to logs:** the request log keeps tool names and time only; source titles name what was read.
5. **MCP servers accept only the AI host:** a shared secret per server (only in `.env`), 127.0.0.1 on the same
   machine, https + a firewall rule on another host (the host refuses plain http to any other host).
6. **Descriptions matter:** the 4B model picks tools by them ("the CURRENT USER's own ...", and what it is NOT for).

## Import directions (checked by `app/tests/test_structure.py`)

`shared` → nothing else in tools · `catalog` → shared · `client` → shared · `host` → catalog, client, shared ·
`server` → catalog, shared. Files in `catalog/` and `server/` may hold several definitions (one tool or one server
per file); everywhere else the project rule "one function or one class per file" applies.
