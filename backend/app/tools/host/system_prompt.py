"""system_prompt(): the system prompt when tools are offered: the 8.1 spike's prompt (69/69), with today's date
and the topics of the offered tools filled in. With the three records tools it is word for word the spike's
prompt (a test checks that). Earlier questions of the conversation are listed for follow-ups."""

from collections.abc import Sequence
from datetime import date

PROMPT = """You are the ITI assistant for Intellismart Technology Inc. employees. Today is {today}.
You are talking to ONE logged-in employee. You can only see THEIR OWN records.
- Questions about company policies, rules or procedures: call search_company_documents.
- Questions about the user's OWN {topics}: call the matching tool.
- If the question names or points to ANOTHER person (a name, an employee number, "my manager", "my colleague"),
  do NOT call any records tool: say you can only show the logged-in employee's own records.
- Every records tool returns ONLY the logged-in employee's own records, never anyone else's.
- Never guess numbers: use only what a tool returns, quote dates and amounts exactly, never calculate new amounts.
- After explaining a deduction, add: "If this looks wrong, please contact HR."
"""


def system_prompt(topics: list[str], today: date, history: Sequence[str] = ()) -> str:
    if len(topics) > 2:
        joined = ", ".join(topics[:-1]) + ", or " + topics[-1]
    else:
        joined = " or ".join(topics)
    text = PROMPT.format(today=today.isoformat(), topics=joined)
    if history:
        text += "\nEarlier questions in this conversation:\n" + "\n".join(f"- {q}" for q in history)
    return text
