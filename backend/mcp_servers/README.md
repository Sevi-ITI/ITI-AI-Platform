# MCP servers (Phase 8.5)

An MCP server lets another system offer **tools** to the ITI chatbot without changing the AI platform's code.
The platform discovers the tools (`ITI_MCP_SERVERS` in `backend\.env`), shows them to the model as
`<server>__<tool>`, and runs the model's calls with the same safety rules as the built-in records tools.

`records_server.py` is the **reference server**: the three records tools (leave credits, absences, payslip
deductions) over MCP, answered by the same fixed queries as the built-in tools. Use it as the template.

## Run the reference server (laptop)

1. In `backend\.env`, the same long random secret twice (letters and digits, 20+ characters):
   ```
   ITI_MCP_RECORDS_TOKEN=<secret>
   ITI_MCP_SERVERS=[{"name": "records", "url": "http://127.0.0.1:8100/mcp", "scope": "records:read", "token": "<secret>"}]
   ```
2. From `backend\`: `python -m mcp_servers.records_server` (listens on 127.0.0.1:8100).
3. Restart uvicorn. Keys with `records:read` are now offered `records__get_my_leave_credits` and the others.

While the built-in records tools are also on (`ITI_RECORDS_DB_URL`), the model sees both sets. To test the MCP
path alone, start uvicorn in a window where `$env:ITI_RECORDS_DB_URL = ""` (the server keeps reading `.env`).

## Rules for any new MCP server

| Rule | Why |
|---|---|
| A per-employee tool takes an `employee_id` argument | The platform removes it from what the model sees and always fills it in from `ITI-User-Id`. The model can never choose whose data is read |
| Refuse every request without `Authorization: Bearer <token>`; compare with `hmac.compare_digest` | Only the platform may call the server: it is the one that sets `employee_id` |
| Listen on 127.0.0.1 when on the same machine; otherwise **https** plus a firewall rule (AI server's IP only) | The platform refuses plain `http://` to any other host |
| Read-only tools; fixed, parameterised queries | The model only fills small, checked arguments |
| Return JSON with only what the answer needs; errors as `ToolError("what was wrong")` | Errors go back to the model as text; never put other people's data in them |
| Clear tool descriptions ("the CURRENT USER's own ...", what it is NOT for) | The 4B model picks tools by their descriptions (Phase 8.4: R3 needed "days USED ... also for past years") |

A C# team can build the same with the official C# MCP SDK: same tool shapes, same `employee_id` and token rules.
