"""host: the WHOLE AI host. One concern per file (Phase 8.6c): everything between a chat question and its tools is
here: which tools a key is offered, the system prompt, running one call, source titles, and the tool loop.
chat calls answer_with_tools(); a documents question returns None and goes to RAG, unchanged.

Safety: employee_id ALWAYS comes from ITI-User-Id (built-in tools refuse it as an argument, MCP tools get it
overwritten); every tool's scope is checked twice (when offered and when run); the request log keeps tool names
and time only, never values."""

import json
import time
from collections.abc import Sequence
from datetime import date

import requests
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import DBAPIError

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError
from app.rag.c_embeddings import OLLAMA_URL
from app.rag.f_chains import CHAT_MODEL, NUM_CTX, TEMPERATURE, TIMEOUT_SECONDS
from app.tools.client import McpTool, call_mcp_tool, company_system, mcp_tools
from app.tools.console_features import feature_on
from app.tools.shared import RECORDS_OF, Tool, ToolSpec, get_records_engine
from app.tools.sql_tools import tool_from_row
from app.tools.store import app_tool_names, company_systems, records_source, sql_tool_rows, tool_overrides
from app.tools.tools import TOOL_REGISTRY

MAX_ROUNDS = 3
NO_ANSWER = "I'm sorry, I couldn't find the answer to that in your records. HR will be glad to help you with it."
# 2026-10-21: after an empty result the model sometimes called the SAME tool with the SAME arguments again (4/20), used
# up the rounds, and the last call without tools then gave only "Let me look that up." A repeat is not run again (the
# model is told its result is final), and the last call gets ANSWER_NOW first.
REPEATED = "You already called this tool with these arguments: its result above is final. Answer from it now."
ANSWER_NOW = ("Answer my question now, using only the tool results above. Don't say you will look something up: "
              "give the answer (if a result is empty, say nothing is on file for that period).")

# --- the documents signal -------------------------------------------------------------------------------------
# Offered next to the tools. The model calls it for any question that is not about the user's own records; the
# answer then comes from RAG (citations, "I don't know"). It is a signal, never run.

DOCUMENTS_TOOL = ToolSpec(
    name="search_company_documents",
    description="Search ITI's company documents: policies, rules, procedures, handbooks. Use it for every question "
    "that is not about the user's OWN leave credits, absences or payslip.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What to look up"}},
        "required": ["query"],
    },
    scope="chat:invoke",
)

# --- the system prompt ----------------------------------------------------------------------------------------
# The 8.1 spike's prompt (69/69): with the three records tools its rules are word for word that prompt (a test checks
# it). TONE (Vince, 2026-10-20) comes after the rules, so being friendly never outranks them.

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

# No example ANSWERS in TONE: with "Sure! Here are your leave credits for 2026." in it the model answered leave
# questions without calling the tool (2/6 vs 6/6, 2026-10-20). Describe the style; never show a sample reply.
# Its first line (2026-10-21): in Filipino, "start with one short friendly line" made the model greet and answer
# WITHOUT the tool (about 2/15 called it; 15/15 without TONE; 40/40 with this line).
TONE = """In ANY language (English, Filipino or Taglish): for the employee's OWN records, call the matching tool FIRST;
never write a greeting or an answer before you have the tool result. About ANOTHER person: no tool (rule above).
How to answer (Markdown: the apps render it):
- Be warm, polite and glad to help, like a friendly customer service agent. Start with one short friendly line,
  then the answer.
- Put the key fact in **bold**: the number, date or status the employee asked about, exactly as the tool gave it.
- Several items: a short bullet list. Three or more items with the same details (dates, statuses, hours): a small
  Markdown table. Keep paragraphs short; no headings.
- When something is pending, cancelled or missing, say it kindly and tell the employee what they can do.
- When a tool returns nothing, say there is nothing on file for that period and suggest HR; never guess why.
- End with the offer of more help on its own line, e.g. "Is there anything else I can help you with?"
- Being friendly never changes the facts: every rule above still applies."""


def system_prompt(topics: list[str], today: date, history: Sequence[str] = ()) -> str:
    joined = ", ".join(topics[:-1]) + ", or " + topics[-1] if len(topics) > 2 else " or ".join(topics)
    text = PROMPT.format(today=today.isoformat(), topics=joined) + "\n" + TONE
    if history:
        text += "\nEarlier questions in this conversation:\n" + "\n".join(f"- {q}" for q in history)
    return text


def topics_for(specs: list[ToolSpec]) -> list[str]:
    """What the offered tools answer, in order, no repeats: a local tool's topic, an MCP server's topics."""
    topics, local, remote = [], local_tools(), mcp_tools()
    for spec in specs:
        if spec.name in local:
            topics.append(local[spec.name].topic)
        elif spec.name in remote:
            topics.extend(remote[spec.name].server.topics)
    return list(dict.fromkeys(topics))


# --- which tools a key is offered -----------------------------------------------------------------------------


def builtin_records_on() -> bool:
    """Local tools answer the records questions: records source "builtin" (console or ITI_RECORDS_SOURCE) and the
    records DB is set."""
    return records_source() == "builtin" and bool(get_settings().records_db_url)


def local_tools() -> dict[str, Tool]:
    """The tools the AI host runs itself: tools.py, plus the SQL tools made in the console (switch "sql_tools")."""
    tools = dict(TOOL_REGISTRY)
    if feature_on("sql_tools"):
        tools.update({row["name"]: tool_from_row(row) for row in sql_tool_rows() if row["enabled"]})
    return tools


def apply_overrides(spec: ToolSpec, overrides: dict) -> ToolSpec | None:
    """None = switched off in the console; a console description replaces the code's (switch "edit_descriptions")."""
    changed = overrides.get(spec.name)
    if not changed:
        return spec
    if not changed["enabled"] and feature_on("tool_switches"):
        return None
    if changed["description"] and feature_on("edit_descriptions"):
        return spec.model_copy(update={"description": changed["description"]})
    return spec


def approval_of(remote: McpTool, overrides: dict) -> str:
    """not_needed: a stdio server from mcp_servers.py (our own code). For a server on another machine (http):
    approved (as it is now), pending (never approved) or changed (its text or arguments changed since)."""
    if remote.server.transport == "stdio":
        return "not_needed"
    approved = overrides.get(remote.spec.name, {}).get("approved")
    if approved is None:
        return "pending"
    return "approved" if approved == remote.spec.fingerprint() else "changed"


def app_list_of(principal: AppPrincipal) -> set[str] | None:
    """The tools an API key's app may use (8.6e-2; a new app has none). None = no list: a console session, which
    has no app (the console's own Chat gets no tool scopes; Try it tests any switched-on tool, super admin only)."""
    return None if principal.key_id is None else app_tool_names(principal.app_id)


def tools_for(principal: AppPrincipal) -> list[ToolSpec]:
    """Local tools (if on) + the usable MCP servers' tools (approved, if from another machine), only those switched
    on, whose scope the key has and that are on the key's app's tool list.
    Console sessions get none in chat: they have no "records:read" and their user id is a username."""
    specs = [tool.spec for tool in local_tools().values()] if builtin_records_on() else []
    overrides = tool_overrides()
    systems = company_systems(principal.company_id)  # 8.6M: a per-company system only with this company's database
    specs += [
        tool.spec
        for tool in mcp_tools().values()
        if approval_of(tool, overrides) in ("not_needed", "approved")
        and company_system(tool.server) in (None, *systems)
    ]
    offered = [apply_overrides(spec, overrides) for spec in specs]
    allowed = app_list_of(principal)
    return [
        spec
        for spec in offered
        if spec is not None and spec.scope in principal.scopes and (allowed is None or spec.name in allowed)
    ]


# --- running one call -----------------------------------------------------------------------------------------


def run_tool(principal: AppPrincipal, employee_id: str, name: str, arguments: dict | None) -> dict:
    """One tool call for the asking employee. Refusals: tool_unknown, tool_off, scope_forbidden, tool_not_allowed
    (not on the app's tool list), tool_bad_arguments, tool_not_approved, records_unavailable, tool_failed,
    tool_unavailable (messages never contain record values)."""
    tool = local_tools().get(name)
    remote = None if tool else mcp_tools().get(name)
    if tool is None and remote is None:
        raise AppError(400, "tool_unknown", f"There is no tool called '{name}'.")
    if tool and not builtin_records_on():
        raise AppError(503, "records_unavailable", "The built-in records tools are off (records source / ITI_RECORDS_DB_URL).")
    overrides = tool_overrides()
    if remote and approval_of(remote, overrides) not in ("not_needed", "approved"):
        raise AppError(403, "tool_not_approved", f"The tool '{name}' waits for a super admin's approval in the console.")
    spec = apply_overrides(tool.spec if tool else remote.spec, overrides)
    if spec is None:
        raise AppError(403, "tool_off", f"The tool '{name}' is switched off in the console.")
    if spec.scope not in principal.scopes:
        raise AppError(403, "scope_forbidden", f"This key may not use '{spec.scope}'.")
    allowed = app_list_of(principal)
    if allowed is not None and name not in allowed:
        raise AppError(403, "tool_not_allowed", f"The tool '{name}' is not on this app's tool list.")
    if remote:
        result = call_mcp_tool(remote, employee_id, arguments if isinstance(arguments, dict) else None, principal.company_id)
        return {"records_of": RECORDS_OF, **result} if remote.per_employee else result
    try:
        args = tool.args.model_validate(arguments or {})
    except ValidationError as error:
        problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'arguments'}: {e['msg']}" for e in error.errors())
        raise AppError(422, "tool_bad_arguments", f"{name}: {problems}") from error
    try:
        with get_records_engine().connect() as conn:
            result = tool.run(conn, employee_id, args)
    except DBAPIError as error:
        raise AppError(503, "records_unavailable", "The records database did not answer. Try again later.") from error
    return {"records_of": RECORDS_OF, **result}


def describe_result(name: str, result: dict) -> tuple[str, str, bool]:
    """(doc_id "<source>:<tool>", source title, holds data). An MCP tool from a server built on tools.py gets the
    same title as the built-in one; any other MCP tool a generic "<Server>: <tool>". Titles never hold values."""
    local = local_tools()
    if name in local:
        tool = local[name]
        title, has_data = tool.describe(result)
        return f"{tool.source}:{name}", title, has_data
    remote = mcp_tools().get(name)
    server, base = (remote.server.name, remote.remote_name) if remote else (name.split("__")[0], name.split("__")[-1])
    if base in TOOL_REGISTRY:
        try:
            title, has_data = TOOL_REGISTRY[base].describe(result)
            return f"{server}:{base}", title, has_data
        except KeyError:  # a different result shape: the generic title below
            pass
    return f"{server}:{base}", f"{server.capitalize()}: {base}", bool(result)


# --- the model ------------------------------------------------------------------------------------------------


def chat_with_tools(messages: list[dict], tools: list[dict] | None) -> dict:
    """One Ollama /api/chat call that may answer with tool calls (same model and settings as RAG).
    Network errors are left to chat (503 llm_unavailable)."""
    body = {
        "model": CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": TEMPERATURE, "num_ctx": NUM_CTX},
    }
    if tools:
        body["tools"] = tools
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()["message"]


# --- the tool loop --------------------------------------------------------------------------------------------


class ToolAnswer(BaseModel):
    """An answer built from tools. sources: one {"doc_id", "title"} per call that worked."""

    answer: str
    found: bool
    sources: list[dict[str, str]]


def answer_with_tools(
    principal: AppPrincipal, employee_id: str, question: str, history: Sequence[str] = (), trace: list[dict] | None = None
) -> ToolAnswer | None:
    """None = a documents question (no tools for this key, no tool call, or a documents call): chat runs RAG.
    Tool errors go back to the model as text; at most MAX_ROUNDS rounds, then one last call without tools.
    trace (only the console's Try it passes one): one {"tool", "arguments", "ms", "error"} is added per call."""
    specs = tools_for(principal)
    if not specs:
        return None
    tools = [DOCUMENTS_TOOL.as_ollama()] + [spec.as_ollama() for spec in specs]
    system = system_prompt(topics_for(specs), date.today(), history)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    used, sources, found, tool_ms = [], [], False, 0
    already_called: set[str] = set()  # name + arguments of every call made for this question

    for _ in range(MAX_ROUNDS):
        message = chat_with_tools(messages, tools)
        calls = message.get("tool_calls") or []
        names = [call["function"]["name"] for call in calls]
        if not calls or (not used and all(name == DOCUMENTS_TOOL.name for name in names)):
            break  # an answer, or a documents question
        messages.append(message)
        for call in calls:
            name, arguments = call["function"]["name"], call["function"].get("arguments")
            start, error_code = time.perf_counter(), None
            same = f"{name} {json.dumps(arguments, sort_keys=True)}"
            if same in already_called:
                if trace is not None:
                    trace.append({"tool": name, "arguments": arguments if isinstance(arguments, dict) else {}, "ms": 0, "error": "repeated_call"})
                messages.append({"role": "tool", "tool_name": name, "content": json.dumps({"error": "repeated_call", "message": REPEATED})})
                continue
            already_called.add(same)
            try:
                if name == DOCUMENTS_TOOL.name:
                    raise AppError(400, "tool_unknown", "Documents can't be searched here: answer from the records.")
                result = run_tool(principal, employee_id, name, arguments)
                doc_id, title, has_data = describe_result(name, result)
                sources.append({"doc_id": doc_id, "title": title})
                found = found or has_data
                content = json.dumps(result)
            except AppError as error:
                error_code = error.code
                content = json.dumps({"error": error.code, "message": error.message})
            ms = int((time.perf_counter() - start) * 1000)
            tool_ms += ms
            used.append(name)
            if trace is not None:
                trace.append({"tool": name, "arguments": arguments if isinstance(arguments, dict) else {}, "ms": ms, "error": error_code})
            messages.append({"role": "tool", "tool_name": name, "content": content})
    else:  # rounds used up: the model must answer now
        message = chat_with_tools(messages + [{"role": "user", "content": ANSWER_NOW}], None)

    if not used:
        return None
    record_metric(tools=",".join(used)[:120], tools_ms=tool_ms)
    return ToolAnswer(answer=(message.get("content") or "").strip() or NO_ANSWER, found=found, sources=sources)
