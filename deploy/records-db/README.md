# Records DB (Phase 8): development copy on the laptop

SQL Server 2022 in Docker with the records tables, the AI's read-only views and **fake** test employees.
The real records DB belongs to the C# apps; these scripts are its development stand-in and the schema
proposal (Phase 8 plan, section 6). Run everything from the repo root in PowerShell.

| File | What |
|---|---|
| `01_schema.sql` | Database `iti_records` and its 8 tables |
| `02_ai_access.sql` | Schema `ai` with 3 views + login `iti_ai_reader` (SELECT on `ai` only) |
| `03_test_data.sql` | Fake employees E-1001 (test), E-1002, E-1003. Never real people |

## Passwords

- `ITI_RECORDS_SA_PASSWORD` in `deploy\.env`: the admin login, only for creating the DB and running these scripts.
- The `iti_ai_reader` password: typed at a prompt below, then put only in `backend\.env` (`ITI_RECORDS_DB_URL`).
- Both: letters and digits only, 20+ characters, upper + lower case + digits. Never in a file that is committed.

## First time

1. Start SQL Server and wait until `docker ps` shows it `healthy` (about 30 s):

   ```powershell
   docker compose -f deploy/docker-compose.records.yaml up -d
   ```

2. Tables:

   ```powershell
   docker compose -f deploy/docker-compose.records.yaml exec records sh -c 'SQLCMDPASSWORD="$MSSQL_SA_PASSWORD" /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -b -i /records-db/01_schema.sql'
   ```

3. Views and the AI login. The reader password is asked at a prompt (not saved in the PowerShell history)
   and removed from the session afterwards:

   ```powershell
   $env:AI_READER_PASSWORD = Read-Host "iti_ai_reader password"
   docker compose -f deploy/docker-compose.records.yaml exec -e AI_READER_PASSWORD records sh -c 'SQLCMDPASSWORD="$MSSQL_SA_PASSWORD" /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -b -i /records-db/02_ai_access.sql'
   Remove-Item Env:AI_READER_PASSWORD
   ```

4. Fake test data:

   ```powershell
   docker compose -f deploy/docker-compose.records.yaml exec records sh -c 'SQLCMDPASSWORD="$MSSQL_SA_PASSWORD" /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -b -i /records-db/03_test_data.sql'
   ```

Each step prints `Changed database context to 'iti_records'.` (step 4 also prints row counts) and no
`Msg ...` error lines.

## Check

From `backend\`: `python -m scripts.check_records_db` ends with `records DB check: ok`.

## Start over

Deletes the database and all its data (fake data only on the laptop), then repeat "First time":

```powershell
docker compose -f deploy/docker-compose.records.yaml down -v
```