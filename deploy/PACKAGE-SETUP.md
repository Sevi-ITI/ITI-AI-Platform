# ITI-AI-Package: setting it up after the install

Do `README.md` first (load the images, settings, start, models). This file continues from a running stack:
1. the admin account, 2. documents and a chat check, 3. MCP and database connections (HR records),
4. API keys for the C# apps. Windows PowerShell, from the package folder. Every command that asks for a password
asks at a hidden prompt: never type a password or key on a command line, in a chat or in an email.

Where things are on this machine:

| What | Address |
|---|---|
| Console (this machine) | http://127.0.0.1:4000 |
| API (this machine) | http://127.0.0.1:8000 (Swagger at /docs) |
| The console on the network and the C# apps (through Caddy, if `door` is on) | the names in `ITI_CONSOLE_SITES` / `ITI_API_SITES` |

## 1. The admin account

The database starts empty: the first super admin is made from the command line, the rest in the Console.

1. The super admin (asks for the login password twice):

       docker compose -f deploy/docker-compose.yaml exec api python -m scripts.create_console_user <username> --role super_admin --name "<Full Name>"

2. Its **security password** (a second password, NOT the login one; it unlocks the risky Tools & MCP actions,
   section 3, for 15 minutes):

       docker compose -f deploy/docker-compose.yaml exec api python -m scripts.set_security_password <username>

3. Sign in at http://127.0.0.1:4000. **Check:** the login page says "AI service connected"; Overview shows the
   database, Ollama and both models green (the GPU card stays blank inside containers: known).
4. More people: Accounts → New account. Roles: **super admin** (everything), **supervisor** (reads every page,
   chats, uploads new documents), **tester** (Chat only, for the collections you give them). Five wrong passwords
   lock an account for 15 minutes; deactivate people instead of deleting them.

## 2. Documents and a chat check

The collection `iti-docs` exists from the first start. Only text PDFs (a scanned PDF fails: no OCR), up to 50 MB.

1. Console → Documents → upload to `iti-docs` (or create another collection first). The job goes
   `queued → running → done` with a chunk count. A job that ends `done` with a **warning** has garbled numbers in
   its text: answers from those pages may be refused; use a cleaner PDF.
2. Many files at once: copy the folder into the API container and use the uploader script with a short-lived key
   (step 4 explains keys; give it the preset "Document uploader", that collection, 7 days):

       docker compose -f deploy/docker-compose.yaml cp "C:\path\to\pdfs" api:/tmp/pdfs
       docker compose -f deploy/docker-compose.yaml exec api bash
       read -rs ITI_SEED_KEY; export ITI_SEED_KEY          # paste the key, Enter (nothing is shown)
       python -m scripts.seed_documents /tmp/pdfs --collection iti-docs
       exit
       docker compose -f deploy/docker-compose.yaml exec -u root api rm -rf /tmp/pdfs   # copied files belong to root

   It prints done / failed per file. Revoke that key afterwards (it can also delete documents).
3. **Chat check** (Console → Chat, collection `iti-docs`):

   | Ask | Passes when |
   |---|---|
   | a question answered in one of the PDFs | an answer citing that file and page |
   | a follow-up ("And for probationary staff?") | it keeps the topic |
   | something not in any document | the polite "please ask HR" reply, no invented answer |
   | the same question in Filipino | a Filipino answer (or the Filipino refusal) |

4. `docker compose -f deploy/docker-compose.yaml exec ollama ollama ps` → the model shows `100% GPU`.

## 3. MCP and database connections (HR records)

Skip this section for a documents-only start. HR answers read the employee's OWN records from the company's
HRDotNet SQL Server through read-only views. They need four things: the views and a reader login on that database,
its address in `backend/.env`, the `hrdotnet` connection in the Console, and the tools ticked per app.

1. **On the HRDotNet SQL Server** (the DBA, as `sa`): the 12 scripts in this package's **`hrdotnet-sql\`** folder,
   in the order of its `README.md`. Change only the `USE [HRDotNet.QA];` line at the top of each to the real database
   name. Run 01–10, then 12, then `11_ai_check.sql` last. For a new reader login, run 02 in SQLCMD mode with
   `:setvar HRDOTNET_READER_PASSWORD "..."` as its first line, then delete that line. **Check:** `11_ai_check.sql`
   prints 14 × `ok ai.v_…`, 3 × `ok dbo blocked`, `reader_is_admin = 0`, `reads_all_tables = 0`.
2. **Network:** this machine must reach that SQL Server on its port (usually 1433). Nothing else needs it.
3. **The address**, in `backend/.env` (typed by hand; URL-encode special characters in the password; never `sa`):

       ITI_HRDOTNET_DB_URL=mssql+mssqlpython://hrdotnet_ai_reader:<password>@<host>:1433/<database>?Encrypt=yes&TrustServerCertificate=yes

   This is the database of the company `iti`. Each other client company gets its own variable, e.g.
   `ITI_DB_ACME_HRDOTNET=...`. Then recreate the API so it reads the file again (`restart` does not):

       docker compose -f deploy/docker-compose.yaml up -d --no-build --force-recreate api

4. **Console → Tools & MCP** (unlock with the security password):
   - Add connection: name **`hrdotnet`** (exactly; the tools become `hrdotnet__…`), transport **stdio**, server
     **hrdotnet**, scope **`hrdotnet:read`**. Test it: 10 tools.
   - Tool switches: **switch `hrdotnet__get_my_payslip` OFF** unless payslips are approved for this machine (on the
     original laptop it is off for privacy; a new database starts with it on).
5. **Console → Companies** → the company's card → "Its hrdotnet database" → **direct** → the variable NAME
   (`ITI_HRDOTNET_DB_URL`, or `ITI_DB_ACME_HRDOTNET`) → **Test**: host, database, reachable. No row = that company is
   never offered the HR tools.
6. **Per app** (Apps & keys, after section 4): tick the `hrdotnet__*` tools on the apps that may use them; their keys
   need the scope `hrdotnet:read`. New apps start with no tools.
7. **Prove it does not leak** before real users (required by the data-privacy approval). With a key that has
   `chat:invoke` + `hrdotnet:read` and the tools ticked:

       docker compose -f deploy/docker-compose.yaml exec api bash
       read -rs ITI_HRDOTNET_CHECK_KEY; export ITI_HRDOTNET_CHECK_KEY
       python -m scripts.check_hrdotnet_isolation --collection <a collection the key may ask>
       exit

   **Passes when:** `0 leak(s)` (with payslip off, its positive control shows "not found": expected). Run it again
   after any change to the HR tools or their database.

Other systems later: an MCP server on another machine is added the same way with transport **http**, its https URL
and the NAME of the `.env` variable holding its secret; its tools wait for a super admin's approval.

## 4. API keys for the C# apps

Keys of the original laptop do not work here: every machine issues its own. A key is shown **once**; only its hash is
stored.

1. **Apps & keys → New app**, one per C# application (e.g. `hr-portal`). For a test set-up a separate dev app
   (e.g. `hr-portal-dev`): its own keys, log and chat history.
2. **Companies** → link the app to the company it serves (a key can only be made for a linked company).
3. **New key** on the app's card: the company, the collections it may ask, the scopes, an expiry:

   | Scope | Give it when |
   |---|---|
   | `chat:invoke` | always (chat, history, suggestions) |
   | `hrdotnet:read` | only if the app shows the employee's own HR records (section 3) |
   | `documents:write` | only an uploader (can also delete documents) |

   Dev keys: short expiry (e.g. 90 days). Production keys: only at go-live, for whoever configures that server.
4. **Hand it over** in person or through a password manager, never by email or chat, with the base URL
   (`https://<ITI_API_SITES name>:8443`) and the collection name. The app keeps it only on its server, as the
   environment variable `ItiAi__ApiKey`; never in a browser, a page, or git. The user id it sends
   (`ITI-User-Id`) comes from the app's own login session, never from the browser.
5. **Check:** the team runs the integration kit's smoke test against the base URL: all PASS lines. Their calls appear
   in Console → Request log.
6. **Later:** rotate a key by minting a new one, swapping it on the app server, then revoking the old one (calls
   with it get 401). A lost key cannot be shown again: rotate it. Revoke the uploader and check keys when done.
