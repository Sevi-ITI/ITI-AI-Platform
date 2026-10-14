-- 01_schema.sql: the records DB tables (Phase 8 plan, section 6). Safe to run once on an empty server.
-- The C# apps write these tables; the AI platform only reads the views of 02_ai_access.sql.
-- Money is DECIMAL(12,2), never float. employee_id is the same text the apps send as ITI-User-Id.

CREATE DATABASE iti_records;
GO
USE iti_records;
GO

CREATE TABLE employees (
    employee_id       VARCHAR(20)  NOT NULL PRIMARY KEY,
    last_name         NVARCHAR(80) NOT NULL,
    first_name        NVARCHAR(80) NOT NULL,
    middle_name       NVARCHAR(80) NULL,
    position          NVARCHAR(80) NOT NULL,
    department        NVARCHAR(80) NOT NULL,
    manager_id        VARCHAR(20)  NULL REFERENCES employees (employee_id),  -- for manager access later (R-9)
    employment_status VARCHAR(20)  NOT NULL,   -- regular, probationary, resigned, ...
    hire_date         DATE         NOT NULL
);

CREATE TABLE salary_history (
    salary_history_id INT IDENTITY PRIMARY KEY,
    employee_id       VARCHAR(20)   NOT NULL REFERENCES employees (employee_id),
    effective_date    DATE          NOT NULL,
    monthly_salary    DECIMAL(12,2) NOT NULL,
    change_type       VARCHAR(20)   NOT NULL,  -- hire, raise, promotion, adjustment
    reason            NVARCHAR(200) NULL
);

CREATE TABLE leave_types (
    leave_type_code VARCHAR(10)  NOT NULL PRIMARY KEY,  -- VL, SL, ...
    name            NVARCHAR(60) NOT NULL,
    is_paid         BIT          NOT NULL
);

CREATE TABLE leave_balances (
    employee_id     VARCHAR(20)  NOT NULL REFERENCES employees (employee_id),
    leave_type_code VARCHAR(10)  NOT NULL REFERENCES leave_types (leave_type_code),
    year            SMALLINT     NOT NULL,
    entitled_days   DECIMAL(5,1) NOT NULL,
    used_days       DECIMAL(5,1) NOT NULL,
    remaining_days  DECIMAL(5,1) NOT NULL,
    PRIMARY KEY (employee_id, leave_type_code, year)
);

CREATE TABLE attendance (
    attendance_id     INT IDENTITY PRIMARY KEY,
    employee_id       VARCHAR(20)   NOT NULL REFERENCES employees (employee_id),
    work_date         DATE          NOT NULL,
    status            VARCHAR(12)   NOT NULL,  -- present, absent, late, on_leave, holiday, rest_day
    time_in           TIME(0)       NULL,
    time_out          TIME(0)       NULL,
    minutes_late      SMALLINT      NOT NULL DEFAULT 0,
    minutes_undertime SMALLINT      NOT NULL DEFAULT 0,
    leave_type_code   VARCHAR(10)   NULL REFERENCES leave_types (leave_type_code),  -- when on_leave
    remarks           NVARCHAR(200) NULL,
    CONSTRAINT uq_attendance_day UNIQUE (employee_id, work_date)
);

CREATE TABLE pay_periods (
    pay_period_id INT IDENTITY PRIMARY KEY,
    period_start  DATE NOT NULL,
    period_end    DATE NOT NULL,
    pay_date      DATE NOT NULL UNIQUE
);

CREATE TABLE payslips (
    payslip_id       INT IDENTITY PRIMARY KEY,
    employee_id      VARCHAR(20)   NOT NULL REFERENCES employees (employee_id),
    pay_period_id    INT           NOT NULL REFERENCES pay_periods (pay_period_id),
    basic_pay        DECIMAL(12,2) NOT NULL,
    total_additions  DECIMAL(12,2) NOT NULL,
    total_deductions DECIMAL(12,2) NOT NULL,
    net_pay          DECIMAL(12,2) NOT NULL,
    CONSTRAINT uq_payslip_period UNIQUE (employee_id, pay_period_id)
);

-- The "why": one row per addition or deduction, linked to the absent / late day when there is one.
CREATE TABLE payslip_lines (
    payslip_line_id INT IDENTITY PRIMARY KEY,
    payslip_id      INT           NOT NULL REFERENCES payslips (payslip_id),
    line_type       VARCHAR(10)   NOT NULL,  -- addition, deduction
    category        VARCHAR(30)   NOT NULL,  -- absence, late, undertime, SSS, PhilHealth, Pag-IBIG, tax, 13th month, ...
    description     NVARCHAR(200) NOT NULL,
    quantity        VARCHAR(20)   NULL,      -- "1 day", "45 min"
    rate            VARCHAR(20)   NULL,      -- "850.00", "1.77/min"
    amount          DECIMAL(12,2) NOT NULL,
    related_date    DATE          NULL,
    attendance_id   INT           NULL REFERENCES attendance (attendance_id),
    rule_code       VARCHAR(20)   NOT NULL
);
GO
