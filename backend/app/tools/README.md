# Tools and MCP (Phase 8): how the chatbot looks things up

The chatbot answers from company documents (RAG) and, for keys with the right scope, from **tools**: small,
read-only lookups such as "the asking employee's leave credits". Everything about tools is in this folder,
**one concern per file**, and **one file per system** in `systems/` (2026-10-21): to change or add something,
you edit one file, and a change to one system's tools never touches another's. All API routes: `app/ROUTES.md`.

| File | What is in it | You open it to... |
|---|---|---|
| `tools.py` | every built-in tool (leave credits, absences, deductions) + the list `TOOLS` | change or add a tool |
| `servers.py` | the **starting set** of connections from the AI host to MCP servers (copied into the DB once; then the console manages them) | only for a fresh database |
| `systems/<name>.py` | **one file per system** we serve over MCP: its server, tools, SQL and helpers (today: `records.py`, `hrdotnet.py`). A system never imports another | change or add a tool of that system |
| `mcp_servers.py` | the list `SERVERS` of our MCP servers (one per system file) + how one is started (stdio / `--http`) | list a new system |
| `host.py` | the AI host: which tools a key gets, the system prompt, the tool loop, running a call | rarely: change how tools are used |
| `client.py` | the MCP client: check a `servers.py` entry, connect, discover, call, cache | rarely: change how servers are reached |
| `shared.py` | `ToolSpec`, `Tool`, the records DB engine, `read_secret`, `RECORDS_OF` | rarely |
| `console_features.py` | **the kill switches** of the console's Tools & MCP page (True / False) | show or hide a part of that page |
| `store.py` | the console's settings in Postgres: connections, records source, tool on/off, descriptions, SQL tools, change log | rarely |
| `sql_tools.py` | the guards for SQL tools written in the console, and turning one into a tool | rarely |
| `admin_api.py` | the API behind the console page (`/v1/admin/tools/...`), super admin only | rarely |
| `new_tool.example`, `systems/new_system.example` | templates: a section to paste into `tools.py` / a whole file to copy into `systems/` | start a new tool / system |

## How a question flows

```
C# app ─/v1/chat─▶ chat ─▶ host.answer_with_tools ─▶ the model sees the key's tools + "search_company_documents"
                                                       ├─ documents / no tool call ─▶ RAG (unchanged)
                                                       └─ a tool call ─▶ host.run_tool (employee_id = ITI-User-Id)
                                                             ├─ built-in (tools.py) ─▶ fixed SQL on the records DB
                                                             └─ "<server>__<tool>" ─▶ client ─▶ MCP server ─▶ its app / DB
```

## The console (Phase 8.6d)

Console → **Tools & MCP** (super admin only) manages, without a restart and with every change logged: who answers the
records questions (built-in or MCP), the MCP connections (stdio: only servers defined in `mcp_servers.py`; http: url +
the NAME of the `.env` variable with the secret), the status of each server, each tool on or off, and (when switched on
in `console_features.py`) tool descriptions and SQL tools. Each part shows only while its switch is True; when False the
API refuses it too. Secrets stay in `backend\.env`; the console only shows "secret set: yes / no".

SQL tools (switch `sql_tools`, off by default) must be one SELECT on ONE `ai.*` view (no JOIN, `,` join, subquery or
UNION) with `WHERE employee_id = :employee_id`, declared arguments only, and run as the read-only `iti_ai_reader`.
The author's WHERE is not trusted: when the tool runs, the code turns it into
`WHERE employee_id = :employee_id AND (<the author's WHERE>)`, so `OR 1=1` or a renamed column can't widen it (S1.3).
Data from two views needs one `ai.*` view that combines them. A check button runs a tool once as a non-existing
employee and shows only the column names.

Try it (switch `try_it`, off by default): one question as a test employee ID (it stands in for `ITI-User-Id`) with the
tool scopes you tick (never `admin` / `documents:write`), through the SAME tool loop as the real chat
(`host.answer_with_tools`, which fills a `trace`). It shows the answer, which tools ran with which arguments, the sources
and the time. It reads REAL records, so: super admin only, and every use goes to the change log (who, test ID, scopes,
tools that ran, outcome; never the question, the arguments or the answer). A documents question is not sent to RAG here:
the panel says so. The 8.6e-3 security password will guard it (the hook is marked in `admin_api.post_try`).

Approval (8.6e, always on, no switch): a tool from a server on another machine (http connection) is offered only after
a super admin approves it in the console. What was approved is its fingerprint (`ToolSpec.fingerprint()`: text +
arguments); if the server changes either, the tool waits for approval again (refused with `tool_not_approved`).
Tools from `tools.py`, SQL tools and stdio servers from `mcp_servers.py` are our own code: no approval needed.

Per-app tool lists (8.6e-2, always on, no switch): an API key gets only the tools ticked for its APP (console → Apps &
keys → the app's card → Tools it may use; table `app_tools` in `store.py`). A new app has none. Refused with
`tool_not_allowed`. A ticked tool that disappears (its MCP server removed) stays on the list as "missing" and offers
nothing until it comes back. Console sessions have no app: Try it tests any switched-on tool.

One database per company (8.6M, always on): a system listed in `shared.COMPANY_DATABASES` (today `hrdotnet`) reads
each client company's OWN database. Console → Companies → the company's card → its hrdotnet database (table
`company_databases` in `store.py`; changes need the security password):
- **direct** (their DB is reachable from the AI server): the NAME of the `.env` variable with its address, e.g.
  `ITI_DB_ACME_HRDOTNET`. For each call the host starts our server with that address as `ITI_HRDOTNET_DB_URL`.
- **relay** (their DB stays inside their network): our same server runs there
  (`python -m app.tools.mcp_servers hrdotnet --http` behind https), plus the NAME of the `.env` variable with its
  secret. Its tools must match ours exactly (fingerprint), else `relay_outdated` until it is updated.
The company comes only from the key. No row, switched off, or an empty `.env` variable = the company is not offered
the tools and a call gets `company_database_missing`, never another company's data. Tool names stay
`hrdotnet__*` for every company, so each app's tool list (Apps & keys) works as before.

## Common changes

| I want to... | Do this, then restart uvicorn |
|---|---|
| **Change a tool** | Edit its section in `tools.py` |
| **Add a tool** on the records DB | Paste `new_tool.example` at the end of `tools.py`, fill it in, add it to `TOOLS`. It works built-in **and** over the records MCP server |
| **Answer records through MCP instead of built-in** | Console → Tools & MCP → Records source → MCP (or `ITI_RECORDS_SOURCE=mcp` in `backend\.env` as the default). The AI host starts the records server itself |
| **Connect an MCP server on another machine** | Put its secret in `backend\.env` (e.g. `ITI_MCP_PAYROLL_TOKEN=...`), then console → Tools & MCP → Add connection (http, url, that variable's name) |
| **Add a tool to a system** (e.g. HRDotNet) | A new section in `systems/hrdotnet.py` (SQL constant + `@hrdotnet.tool` function), then tick it on the app's card |
| **Add an MCP server for a new system on this machine** | Copy `systems/new_system.example` to `systems/<name>.py`, add it to `SERVERS` in `mcp_servers.py`, add its `servers.py` entry (or console connection) |
| **Switch a server or a tool off** | Console → Tools & MCP (connection: Enabled off; tool: its switch) |
| **Give an app access** | Its key needs the tool's scope (`records:read`, "Chat + own records") AND the tool ticked on the app's card (Apps & keys → Tools it may use) |
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
3. **Every tool has a scope and must be on the app's tool list**, both checked when offered (`tools_for`) and when run (`run_tool`).
4. **Values never go to logs:** the request log keeps tool names and time; source titles name what was read.
5. **Secrets only in `backend\.env`**, never in `servers.py` or any committed file.
6. **Descriptions matter:** the 4B model picks tools by them ("the CURRENT USER's own ...", and what it is NOT for).

## Import directions (checked by `app/tests/test_structure.py`)

`servers.py`, `shared.py`, `console_features.py` import no other tools file · `store.py` → servers · `tools.py`, `sql_tools.py`
→ shared · `client.py` → shared, store · `host.py` → tools, client, shared, store, sql_tools, console_features ·
`systems/<name>.py` → shared, tools (never another system) · `mcp_servers.py` → shared, systems · `admin_api.py` → the
others. In `app/tools/` the rule is one concern per file and one file per system; everywhere else in the backend it stays one function or one class per file.
