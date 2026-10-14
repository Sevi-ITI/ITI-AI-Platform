# Tools and MCP (Phase 8): how the chatbot looks things up

The chatbot answers from company documents (RAG) and, for keys with the right scope, from **tools**: small,
read-only lookups such as "the asking employee's leave credits". Everything about tools is in this folder,
**one concern per file**: to change or add something, you edit one file. All API routes: `app/ROUTES.md`.

| File | What is in it | You open it to... |
|---|---|---|
| `tools.py` | every built-in tool (leave credits, absences, deductions) + the list `TOOLS` | change or add a tool |
| `servers.py` | every connection from the AI host to an MCP server | connect, switch on/off, or add an MCP server |
| `mcp_servers.py` | every MCP server we run ourselves (today: `records`) | add a server for a new system |
| `host.py` | the AI host: which tools a key gets, the system prompt, the tool loop, running a call | rarely: change how tools are used |
| `client.py` | the MCP client: check a `servers.py` entry, connect, discover, call, cache | rarely: change how servers are reached |
| `shared.py` | `ToolSpec`, `Tool`, the records DB engine, `read_secret`, `RECORDS_OF` | rarely |
| `new_tool.example`, `new_mcp_server.example` | templates: a section to paste into `tools.py` / `mcp_servers.py` | start a new tool / server |

## How a question flows

```
C# app ─/v1/chat─▶ chat ─▶ host.answer_with_tools ─▶ the model sees the key's tools + "search_company_documents"
                                                       ├─ documents / no tool call ─▶ RAG (unchanged)
                                                       └─ a tool call ─▶ host.run_tool (employee_id = ITI-User-Id)
                                                             ├─ built-in (tools.py) ─▶ fixed SQL on the records DB
                                                             └─ "<server>__<tool>" ─▶ client ─▶ MCP server ─▶ its app / DB
```

## Common changes

| I want to... | Do this, then restart uvicorn |
|---|---|
| **Change a tool** | Edit its section in `tools.py` |
| **Add a tool** on the records DB | Paste `new_tool.example` at the end of `tools.py`, fill it in, add it to `TOOLS`. It works built-in **and** over the records MCP server |
| **Answer records through MCP instead of built-in** | `ITI_RECORDS_SOURCE=mcp` in `backend\.env` (back: `builtin` or remove the line). That is all: the AI host starts the records server itself |
| **Connect an MCP server on another machine** | Copy the http EXAMPLE in `servers.py`, put its secret in `backend\.env` under its `token_env` |
| **Add an MCP server for a new system on this machine** | Paste `new_mcp_server.example` into `mcp_servers.py`, add it to `SERVERS`, add its `servers.py` entry |
| **Switch a server off** | `"enabled": False` in `servers.py` |
| **Give an app access** | Its key needs the tool's scope (`records:read`): console → Apps & keys → "Chat + own records" |
| **A new kind of access** (e.g. `tickets:read`) | Add it to `Scope` in `app/admin/a_schemas/key_create.py` (+ a console preset) |

Checks: from `backend\`: `ruff check .`, `pytest -q`, then `python -m scripts.check_records_chat` (live) and
`python -m scripts.check_records_isolation` (prompts must never reach another employee's data).

## stdio or http

- **stdio** (servers on this machine): the AI host starts `python -m app.tools.mcp_servers <name>` itself for each
  use. No window, no port, no secret: only the process that started the server can talk to it. Each use starts a
  process, about 1.5 s on the laptop, so an MCP records answer is about that much slower than built-in.
- **http** (servers on another machine): a url and a shared secret. Plain `http://` only to 127.0.0.1 / localhost,
  otherwise https + a firewall rule that lets only the AI server in (Phase 9). Our own server can also run this way:
  `python -m app.tools.mcp_servers records --http` (127.0.0.1:8100, secret `ITI_MCP_RECORDS_TOKEN`).

## Rules every tool and server follows

1. **The model never chooses whose data is read.** No `employee_id` in what the model sees; the host fills it in
   from `ITI-User-Id` (built-in: refused as an argument; MCP: removed from the schema, overwritten on every call).
   `scripts/check_records_isolation.py` tries 12 prompt attacks to prove it.
2. **Read-only, fixed queries:** bound parameters, `WHERE employee_id = :employee_id`, views in schema `ai` only.
3. **Every tool has a scope**, checked when offered (`tools_for`) and when run (`run_tool`).
4. **Values never go to logs:** the request log keeps tool names and time; source titles name what was read.
5. **Secrets only in `backend\.env`**, never in `servers.py` or any committed file.
6. **Descriptions matter:** the 4B model picks tools by them ("the CURRENT USER's own ...", and what it is NOT for).

## Import directions (checked by `app/tests/test_structure.py`)

`servers.py` and `shared.py` import no other tools file · `tools.py` → shared · `client.py` → servers, shared ·
`host.py` → tools, client, shared · `mcp_servers.py` → tools, shared. In `app/tools/` the rule is one concern per
file; everywhere else in the backend it stays one function or one class per file.
