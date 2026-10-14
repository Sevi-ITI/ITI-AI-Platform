-- 02_ai_access.sql: what the AI platform may read. Run after 01_schema.sql.
-- The login's password is passed in by sqlcmd (-v AI_READER_PASSWORD=...), so it is never in this file.
-- The AI login can SELECT from schema "ai" only: no tables, no writes. The views reach the dbo tables
-- through ownership chaining (both owned by dbo). Each view has only the columns one tool needs.

USE iti_records;
GO
CREATE SCHEMA ai AUTHORIZATION dbo;
GO

-- get_my_leave_credits
CREATE VIEW ai.v_leave_balances AS
SELECT b.employee_id, b.year, t.leave_type_code, t.name AS leave_name,
       b.entitled_days, b.used_days, b.remaining_days
FROM dbo.leave_balances AS b
JOIN dbo.leave_types AS t ON t.leave_type_code = b.leave_type_code;
GO

-- get_my_absences (everything that is not a normal day)
CREATE VIEW ai.v_absences AS
SELECT a.employee_id, a.work_date, a.status, a.minutes_late, a.minutes_undertime,
       t.name AS leave_name, a.remarks
FROM dbo.attendance AS a
LEFT JOIN dbo.leave_types AS t ON t.leave_type_code = a.leave_type_code
WHERE a.status IN ('absent', 'late', 'on_leave') OR a.minutes_undertime > 0;
GO

-- explain_my_deductions
CREATE VIEW ai.v_payslip_lines AS
SELECT p.employee_id, pp.pay_date, pp.period_start, pp.period_end,
       l.line_type, l.category, l.description, l.quantity, l.rate, l.amount, l.related_date, l.rule_code
FROM dbo.payslip_lines AS l
JOIN dbo.payslips AS p ON p.payslip_id = l.payslip_id
JOIN dbo.pay_periods AS pp ON pp.pay_period_id = p.pay_period_id;
GO

CREATE LOGIN iti_ai_reader WITH PASSWORD = '$(AI_READER_PASSWORD)', CHECK_POLICY = ON, DEFAULT_DATABASE = iti_records;
GO
CREATE USER iti_ai_reader FOR LOGIN iti_ai_reader;
GRANT SELECT ON SCHEMA::ai TO iti_ai_reader;
GO

