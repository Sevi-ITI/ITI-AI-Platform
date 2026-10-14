# MCP servers

An MCP server lets a system offer **tools** to the ITI chatbot. The AI host connects to the servers listed in
`app/tools/client/servers.py`, shows their tools to the model as `<server>__<tool>`, and runs the model's calls
with the same safety rules as the built-in tools. Overview of the whole folder: `app/tools/README.md`.

`records_server.py` is the **reference server**: it offers every tool of `app/tools/catalog/` over MCP, answered
by the same code (a tool added to the catalog appears here too). `_new_server.py.example` is the template for a
server for another system.

## Run the records server (laptop)

1. In `backend\.env`: `ITI_MCP_RECORDS_TOKEN=<secret>` (letters and digits, 20+ characters). The same variable is
   read by the server (to check) and by the AI host (to send).
2. In `app/tools/client/servers.py`, the `records` entry: `"enabled": True`.
3. From `backend\`: `python -m app.tools.server.records_server` (listens on 127.0.0.1:8100). Restart uvicorn.

Decision D6: normally keep `"enabled": False` for `records`, so the built-in tools answer. With both on, the model
sees each records tool twice (it works, but it is not the intended setup). To test the MCP path alone: put `#`
before `ITI_RECORDS_DB_URL` in `backend\.env`, start the server in a window where
`$env:ITI_RECORDS_DB_URL = Read-Host "records DB URL"` was run (paste the URL), then restart uvicorn.
(`$env:ITI_RECORDS_DB_URL = ""` does not work: Windows deletes an empty variable, and `.env` is read again.)

## Connections of a server

At the top of each server file: `HOST, PORT` (where it listens), `TOKEN_ENV` (the secret the AI host sends), and
what it reads (the records server: the records DB through `ITI_RECORDS_DB_URL`). The matching AI-host side is its
entry in `client/servers.py` (url, token_env, scope, topics).

## Rules for any new MCP server

| Rule | Why |
|---|---|
| A per-employee tool takes an `employee_id` argument | The AI host removes it from what the model sees and always fills it in from `ITI-User-Id`. The model can never choose whose data is read |
| Refuse every request without `Authorization: Bearer <secret>`; compare with `hmac.compare_digest` | Only the AI host may call the server: it is the one that sets `employee_id` |
| 127.0.0.1 on the same machine; otherwise **https** plus a firewall rule (AI server's IP only) | The AI host refuses plain `http://` to any other host |
| Read-only tools; fixed, parameterised queries | The model only fills small, checked arguments |
| Return JSON with only what the answer needs; errors as `ToolError("what was wrong")` | Errors go back to the model as text; never put other people's data in them |
| Clear tool descriptions ("the CURRENT USER's own ...", what it is NOT for) | The 4B model picks tools by their descriptions |

A C# team can build the same with the official C# MCP SDK: same tool shapes, same `employee_id` and secret rules.
