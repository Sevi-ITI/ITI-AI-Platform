# hrdotnet-sql: connect an HRDotNet database to the ITI AI Platform

These 12 scripts prepare ONE HRDotNet database so the assistant can answer an employee's questions about their OWN
records (leave, attendance, schedule, overtime, time logs, requests, employment, payslips, holidays). They create a
schema `ai` with whitelisted, read-only views and a login `hrdotnet_ai_reader` that can read those views and nothing
else. They change no HRDotNet table and hold no password. All are safe to run again (`CREATE OR ALTER`, "only if
missing"). Run them on the SQL Server, as `sa` or the DBA, in SQL Server Management Studio (SSMS).

## Before you run them

1. In **every** file, change only the `USE [HRDotNet.QA];` line near the top to this database's name, e.g.
   `USE [HRDotNet];`. Nothing else needs editing.
2. Pick the reader's password (a long one; keep it in a password manager). It never goes into a file.

## Run order

| # | File | What it does | How |
|---|---|---|---|
| 1 | `01_ai_views.sql` | the schema `ai` | normal |
| 2 | `02_ai_reader.sql` | the login and user `hrdotnet_ai_reader`: SELECT on `ai` only; no `dbo` tables, no writes, no procedures, not admin | **new login:** Query → SQLCMD Mode, add `:setvar HRDOTNET_READER_PASSWORD "<password>"` as line 1, run, then **delete that line before saving**. Login already on this server: normal |
| 3 | `03_ai_views_id_employee.sql` | leave balances and leave applications | normal |
| 4 | `04_ai_view_attendance.sql` | processed attendance | normal |
| 5 | `05_ai_views_schedule.sql` | schedule changes, weekly schedule, usual shift | normal |
| 6 | `06_ai_view_overtime.sql` | overtime applications | normal |
| 7 | `07_ai_view_time_logs.sql` | raw clock punches | normal |
| 8 | `08_ai_view_requests.sql` | official business, missed logs, offsets | normal |
| 9 | `09_ai_views_employment.sql` | employment info and career movements (no pay, bank or Confi columns) | normal |
| 10 | `10_ai_view_payroll.sql` | POSTED payslips and their lines (no names, rates, bank or employer shares) | normal |
| 11 | `12_ai_view_holidays.sql` | the company's holidays (national and local) | normal |
| 12 | `11_ai_check.sql` | **the final check, last** (after 12): changes nothing | normal |

Each view script ends with its own count checks (counts only, never employee rows).

## What `11_ai_check.sql` must show

- 14 × `ok ai.v_...` and 3 × `ok dbo blocked (...)`: in the **Messages** tab, not the result grid. `BROKEN` or
  `MISSING` names the view whose script to fix and run again.
- `reader_is_admin = 0`, `reads_all_tables = 0`, `default_db` = this database.
- Five lookup lists: compare each with the expected codes in the comment at the end of its line in the file. A
  different code gives wrong answers (not an error): check the view that uses it before trusting the tools.

## After the scripts

Continue with `SETUP.md`, part 3: the address in `backend\.env` (as `hrdotnet_ai_reader`, never `sa`), the `hrdotnet`
connection in Tools & MCP, the company's database on the Companies page, the tools per app, and the leak check.

After every HRDotNet upgrade, run `11_ai_check.sql` again.
