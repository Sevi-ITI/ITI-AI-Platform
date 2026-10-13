"""answer_with_tools(): answers a question from the asking employee's records, or returns None when it is a
documents question (then chat runs the normal RAG pipeline, unchanged).

- No tools for this key (no "records:read", or no records DB): None at once, no model call.
- The model sees the records tools + search_company_documents. No tool call, or a documents call: None.
  So any answer that is not built from records tools comes from RAG, with its citations and "I don't know".
- Records calls run through run_tool with the caller's employee id; errors go back to the model as text,
  so it can correct the call or tell the user. At most MAX_ROUNDS rounds, then one last call without tools.
- Records the tools used and their time in the request log; never their values."""

import json
import time
from collections.abc import Sequence
from datetime import date

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError
from app.tools.a_schemas.documents_tool import DOCUMENTS_TOOL
from app.tools.a_schemas.records_prompt import RECORDS_PROMPT
from app.tools.a_schemas.tool_answer import ToolAnswer
from app.tools.c_repository.chat_with_tools import chat_with_tools
from app.tools.d_service.describe_result import describe_result
from app.tools.d_service.run_tool import run_tool
from app.tools.d_service.tools_for import tools_for

MAX_ROUNDS = 3
NO_ANSWER = "I couldn't answer that from your records. Please contact HR."


def answer_with_tools(
    principal: AppPrincipal, employee_id: str, question: str, history: Sequence[str] = ()
) -> ToolAnswer | None:
    specs = tools_for(principal)
    if not specs:
        return None
    tools = [DOCUMENTS_TOOL.as_ollama()] + [spec.as_ollama() for spec in specs]
    system = RECORDS_PROMPT.format(today=date.today().isoformat())
    if history:
        system += "\nEarlier questions in this conversation:\n" + "\n".join(f"- {q}" for q in history)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    used, sources, found, tool_ms = [], [], False, 0

    for _ in range(MAX_ROUNDS):
        message = chat_with_tools(messages, tools)
        calls = message.get("tool_calls") or []
        names = [call["function"]["name"] for call in calls]
        if not calls or (not used and all(name == DOCUMENTS_TOOL.name for name in names)):
            break  # an answer, or a documents question
        messages.append(message)
        for call in calls:
            name, arguments = call["function"]["name"], call["function"].get("arguments")
            start = time.perf_counter()
            try:
                if name == DOCUMENTS_TOOL.name:
                    raise AppError(400, "tool_unknown", "Documents can't be searched here: answer from the records.")
                result = run_tool(principal, employee_id, name, arguments)
                title, has_data = describe_result(name, result)
                sources.append({"tool": name, "title": title})
                found = found or has_data
                content = json.dumps(result)
            except AppError as error:
                content = json.dumps({"error": error.code, "message": error.message})
            tool_ms += int((time.perf_counter() - start) * 1000)
            used.append(name)
            messages.append({"role": "tool", "tool_name": name, "content": content})
    else:
        message = chat_with_tools(messages, None)  # rounds used up: the model must answer now

    if not used:
        return None
    record_metric(tools=",".join(used)[:120], tools_ms=tool_ms)
    return ToolAnswer(answer=(message.get("content") or "").strip() or NO_ANSWER, found=found, sources=sources)
