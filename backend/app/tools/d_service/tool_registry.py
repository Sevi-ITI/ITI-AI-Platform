"""TOOL_REGISTRY: every tool the chat model can be offered, by name. Adding a tool = one entry here.
Descriptions say "the CURRENT USER's own": the model must never use a records tool for someone else."""

from app.tools.a_schemas.absences_args import AbsencesArgs
from app.tools.a_schemas.deductions_args import DeductionsArgs
from app.tools.a_schemas.leave_credits_args import LeaveCreditsArgs
from app.tools.a_schemas.tool import Tool
from app.tools.a_schemas.tool_spec import ToolSpec
from app.tools.d_service.explain_my_deductions import explain_my_deductions
from app.tools.d_service.get_my_absences import get_my_absences
from app.tools.d_service.get_my_leave_credits import get_my_leave_credits

RECORDS_READ = "records:read"

LEAVE_CREDITS = Tool(
    spec=ToolSpec(
        name="get_my_leave_credits",
        description="Get the CURRENT USER's own leave credits (entitled, used, remaining) per leave type for a year.",
        parameters={
            "type": "object",
            "properties": {"year": {"type": "integer", "description": "Calendar year, e.g. 2026. Leave out for this year"}},
        },
        scope=RECORDS_READ,
    ),
    args=LeaveCreditsArgs,
    run=get_my_leave_credits,
)

ABSENCES = Tool(
    spec=ToolSpec(
        name="get_my_absences",
        description="List the CURRENT USER's own absences, late arrivals, undertime and leave days between two dates.",
        parameters={
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "First day, YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "Last day, YYYY-MM-DD"},
            },
            "required": ["date_from", "date_to"],
        },
        scope=RECORDS_READ,
    ),
    args=AbsencesArgs,
    run=get_my_absences,
)

DEDUCTIONS = Tool(
    spec=ToolSpec(
        name="explain_my_deductions",
        description="Get the deduction and addition lines of the CURRENT USER's own payslip, "
        "with the reason, rule, date and amount of each line.",
        parameters={
            "type": "object",
            "properties": {"pay_date": {"type": "string", "description": "Payslip pay date YYYY-MM-DD. Leave out for the latest"}},
        },
        scope=RECORDS_READ,
    ),
    args=DeductionsArgs,
    run=explain_my_deductions,
)

TOOL_REGISTRY = {tool.spec.name: tool for tool in (LEAVE_CREDITS, ABSENCES, DEDUCTIONS)}
