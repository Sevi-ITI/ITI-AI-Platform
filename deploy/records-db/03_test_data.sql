-- 03_test_data.sql: FAKE employees for development and tests. Never real people, never real pay.
-- E-1001 is the test employee (same data as the 8.1 spike); E-1002 and E-1003 exist so tests can
-- prove that one employee never sees another's rows.

USE iti_records;
GO

INSERT INTO employees VALUES
 ('E-1003', N'Reyes',     N'Carla', NULL,     N'Operations Manager', N'Operations', NULL,     'regular', '2019-06-03'),
 ('E-1001', N'Test',      N'Tina',  N'Q.',    N'Staff Engineer',     N'Operations', 'E-1003', 'regular', '2023-02-01'),
 ('E-1002', N'Sample',    N'Sam',   NULL,     N'Accounting Staff',   N'Finance',    'E-1003', 'regular', '2024-08-15');

INSERT INTO salary_history (employee_id, effective_date, monthly_salary, change_type, reason) VALUES
 ('E-1001', '2023-02-01', 30000.00, 'hire',  N'Starting salary'),
 ('E-1001', '2026-01-01', 34000.00, 'raise', N'Annual review 2025'),
 ('E-1002', '2024-08-15', 28000.00, 'hire',  N'Starting salary'),
 ('E-1003', '2019-06-03', 60000.00, 'hire',  N'Starting salary');

INSERT INTO leave_types VALUES ('VL', N'Vacation leave', 1), ('SL', N'Sick leave', 1);

INSERT INTO leave_balances VALUES
 ('E-1001', 'VL', 2026, 15, 8, 7),  ('E-1001', 'SL', 2026, 15, 3, 12),
 ('E-1001', 'VL', 2025, 15, 14, 1), ('E-1001', 'SL', 2025, 15, 5, 10),
 ('E-1002', 'VL', 2026, 15, 2, 13), ('E-1002', 'SL', 2026, 15, 0, 15);

INSERT INTO attendance (employee_id, work_date, status, time_in, time_out, minutes_late, leave_type_code, remarks) VALUES
 ('E-1001', '2026-09-02', 'present',  '08:00', '17:00', 0,  NULL, NULL),
 ('E-1001', '2026-09-03', 'absent',   NULL,    NULL,    0,  NULL, N'no leave filed'),
 ('E-1001', '2026-09-17', 'late',     '08:45', '17:00', 45, NULL, NULL),
 ('E-1001', '2026-10-06', 'on_leave', NULL,    NULL,    0,  'VL', N'approved'),
 ('E-1001', '2026-10-08', 'absent',   NULL,    NULL,    0,  NULL, N'no leave filed'),
 ('E-1002', '2026-09-10', 'absent',   NULL,    NULL,    0,  NULL, N'no leave filed');

INSERT INTO pay_periods (period_start, period_end, pay_date) VALUES
 ('2026-09-01', '2026-09-15', '2026-09-15'),
 ('2026-09-16', '2026-09-30', '2026-09-30');

INSERT INTO payslips (employee_id, pay_period_id, basic_pay, total_additions, total_deductions, net_pay) VALUES
 ('E-1001', 1, 17000.00, 1000.00,  200.00, 17800.00),
 ('E-1001', 2, 17000.00, 1000.00, 1754.69, 16245.31),
 ('E-1002', 2, 14000.00, 1000.00, 1393.33, 13606.67);
GO

DECLARE @p15 INT = (SELECT payslip_id FROM payslips WHERE employee_id = 'E-1001' AND pay_period_id = 1);
DECLARE @p30 INT = (SELECT payslip_id FROM payslips WHERE employee_id = 'E-1001' AND pay_period_id = 2);
DECLARE @s30 INT = (SELECT payslip_id FROM payslips WHERE employee_id = 'E-1002' AND pay_period_id = 2);
DECLARE @abs INT = (SELECT attendance_id FROM attendance WHERE employee_id = 'E-1001' AND work_date = '2026-09-03');
DECLARE @late INT = (SELECT attendance_id FROM attendance WHERE employee_id = 'E-1001' AND work_date = '2026-09-17');
DECLARE @sabs INT = (SELECT attendance_id FROM attendance WHERE employee_id = 'E-1002' AND work_date = '2026-09-10');

INSERT INTO payslip_lines (payslip_id, line_type, category, description, quantity, rate, amount, related_date, attendance_id, rule_code) VALUES
 (@p15, 'deduction', 'Pag-IBIG',   N'Pag-IBIG contribution',      NULL,     NULL,       200.00, NULL,         NULL,  'GOV-HDMF'),
 (@p15, 'addition',  'allowance',  N'Rice allowance',             NULL,     NULL,      1000.00, NULL,         NULL,  'ALW-RICE'),
 (@p30, 'deduction', 'absence',    N'Absent without filed leave', '1 day',  '850.00',   850.00, '2026-09-03', @abs,  'ABS-1'),
 (@p30, 'deduction', 'late',       N'Late arrival',               '45 min', '1.77/min',  79.69, '2026-09-17', @late, 'LATE-1'),
 (@p30, 'deduction', 'SSS',        N'SSS contribution',           NULL,     NULL,       450.00, NULL,         NULL,  'GOV-SSS'),
 (@p30, 'deduction', 'PhilHealth', N'PhilHealth contribution',    NULL,     NULL,       375.00, NULL,         NULL,  'GOV-PH'),
 (@p30, 'addition',  'allowance',  N'Rice allowance',             NULL,     NULL,      1000.00, NULL,         NULL,  'ALW-RICE'),
 (@s30, 'deduction', 'absence',    N'Absent without filed leave', '1 day',  '700.00',   700.00, '2026-09-10', @sabs, 'ABS-1'),
 (@s30, 'deduction', 'SSS',        N'SSS contribution',           NULL,     NULL,       393.33, NULL,         NULL,  'GOV-SSS'),
 (@s30, 'deduction', 'PhilHealth', N'PhilHealth contribution',    NULL,     NULL,       300.00, NULL,         NULL,  'GOV-PH'),
 (@s30, 'addition',  'allowance',  N'Rice allowance',             NULL,     NULL,      1000.00, NULL,         NULL,  'ALW-RICE');
GO

