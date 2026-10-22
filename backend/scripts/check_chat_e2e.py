"""check_chat_e2e: every chat route once, end to end, the way a C# app calls them (pre-demo smoke test).
Each question is asked ONE time (no retry loops). Prints one line per check: PASS/FAIL, seconds, why. It never prints
an answer's text (Part 6 reads real HRDotNet data), only verdicts, citation file names and tool names.

- Part 1, refused calls (no model call): no key / wrong key 401, no ITI-User-Id 422, empty and too-long question 422,
  a collection the key may not read 403/404, an unknown conversation 404, and (optional) a key without chat:invoke 403.
- Part 2, GET /v1/suggestions: 200 and a list.
- Part 3, POST /v1/chat: a documents question (found, a citation with a page), an off-topic question (the
  "I don't know" reply: found=false, no citations), and a follow-up in the same conversation.
- Part 4, POST /v1/chat/stream: events in order meta -> token(s) -> done, done has answer/found/citations.
- Part 5, history: both conversations in GET /v1/conversations, the messages in order (user, assistant, ...);
  ANOTHER user id gets 404 on them and does not see them in its list.
- Part 6, HRDotNet tools as --hr-user (default 10): R1-R9 one question per tool; R10-R15 own dates, an older year,
  Tagalog, two tools in one question; R16 a follow-up in the same conversation; R17 through the stream. Each reply
  must cite the expected tool(s) and not be empty. Skip it with --no-hr.
- Part 7, edge cases (skip with --no-edge). It first reads the real values from the ai views (ITI_HRDOTNET_DB_URL) and
  keeps them in memory; lines say only how many matched, never a value.
  7A V1-V5 the values are right: latest net pay, Oct-Dec 2025 gross and net, every leave type's remaining days,
     the employee number, the overtime document numbers.
  7B N1-N3 no data, nothing invented: a month with no payslip, 30 days with no overtime, a future payslip. Pass: no
     peso amount in the answer (found=false or a "no record" reply).
  7C P1-P3 out-of-range periods (a year of attendance, 3 months of schedule, an end date before the start): a 200
     with a non-empty answer, no 500.
  7D U1-U3 an unknown employee id (numeric, not in the views; and non-numeric): no peso amount, none of --hr-user's
     values, no employee number.
  7E K1-K3 a TERMINATED employee (date_ended set; Vince 2026-10-23: they get ONLY the latest posted payslip):
     the latest payslip comes back; an older payslip and the other tools do not.
  7F M1-M2 a policy AND own-records question at once: the reply must cite a document AND the tool.
- --hr-down (a separate run, only D1-D2): with the HR database made unreachable in the console, an HR question must
  get a clean reply (200 without peso amounts, or a 503), never a 500 or made-up figures. See the runbook.
Needs uvicorn, Ollama, a key with chat:invoke for the collection (in $env:ITI_CHAT_CHECK_KEY); Parts 6-7 need the key
to have hrdotnet:read and the 9 hrdotnet__* tools ticked and ITI_HRDOTNET_DB_URL set (the HRDotNet check key works for
everything). About 42 model calls in all.
Optional: $env:ITI_CHAT_NOSCOPE_KEY = a key WITHOUT chat:invoke (for the 403 check; skipped without it).

Run from backend\\:
    $env:ITI_CHAT_CHECK_KEY = Read-Host "chat check key"
    python -m scripts.check_chat_e2e --collection iti-policies
    python -m scripts.check_chat_e2e --collection iti-policies --no-hr
    python -m scripts.check_chat_e2e --collection iti-policies --hr-down
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import date, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import text

from app.tools.systems.hrdotnet import get_hrdotnet_engine

OFF_TOPIC = "What is the best recipe for chocolate chip cookies?"
FOLLOW_UP = "Can you say that again in one short sentence?"
HR_QUESTIONS = [  # (id, tools that must ALL be cited, question): the asker's own records only
    # one per tool, each tool's default period
    ("R1", ("get_my_leave_credits",), "How many leave credits do I have left this year?"),
    ("R2", ("get_my_leave_applications",), "Show my leave applications this year."),
    ("R3", ("get_my_attendance",), "Was I late or absent this month?"),
    ("R4", ("get_my_schedule",), "What is my work schedule this week?"),
    ("R5", ("get_my_overtime",), "Show my overtime applications in the last 30 days."),
    ("R6", ("get_my_time_logs",), "Show my clock punches this week."),
    ("R7", ("get_my_requests",), "Show my official business and missed log requests in the last 30 days."),
    ("R8", ("get_my_employment_info",), "What is my position and employee number?"),
    ("R9", ("get_my_payslip",), "Show my latest payslip."),
    # the way people really ask: own dates, older periods, Tagalog, two tools at once
    ("R10", ("get_my_payslip",), "Show my payslips for October to December 2025 with the gross and net pay."),
    ("R11", ("get_my_leave_credits",), "How many leave credits did I have in 2025?"),
    ("R12", ("get_my_attendance",), "Was I late or absent from September 1 to September 30, 2026?"),
    ("R13", ("get_my_payslip",), "Magkano ang net pay ko sa huling payslip?"),
    ("R14", ("get_my_schedule",), "Ano ang schedule ko ngayong linggo?"),
    ("R15", ("get_my_leave_credits", "get_my_attendance"), "How many leave credits do I have left, and was I late this month?"),
]
HR_FOLLOW_UP = ("R16", ("get_my_payslip",), "Show my latest payslip.", "What about the payslip before that one?")
HR_STREAMED = ("R17", ("get_my_employment_info",), "When was I hired, and what is my current position?")


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def line(self, check_id: str, ok: bool, seconds: float, why: str) -> bool:
        self.passed += ok
        self.failed += not ok
        print(f"{check_id:4} {'PASS' if ok else 'FAIL'} {seconds:5.1f}s  {why}", flush=True)
        return ok


def code_of(response) -> str:
    try:
        return response.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return ""


def timed(call):
    start = time.perf_counter()
    result = call()
    return result, time.perf_counter() - start


def expect_error(report, check_id, call, statuses: tuple[int, ...], label: str) -> None:
    response, seconds = timed(call)
    ok = response.status_code in statuses
    report.line(check_id, ok, seconds, f"{label}: HTTP {response.status_code} {code_of(response)}".strip())


def sources(body: dict) -> list[str]:
    return [c["doc_id"] for c in body.get("citations") or []]


def part1_refused(client, report, headers, collection, noscope_key) -> None:
    print("\n-- Part 1: refused calls")
    body = {"question": "How do I file a leave?", "collection": collection}
    user = {"ITI-User-Id": headers["ITI-User-Id"]}
    expect_error(report, "E1", lambda: client.post("/v1/chat", headers=user, json=body), (401,), "no key")
    expect_error(report, "E2", lambda: client.post("/v1/chat", headers={**user, "ITI-Api-Key": "iti_sk_wrong"}, json=body),
                 (401,), "wrong key")
    expect_error(report, "E3", lambda: client.post("/v1/chat", headers={"ITI-Api-Key": headers["ITI-Api-Key"]}, json=body),
                 (422,), "no ITI-User-Id")
    expect_error(report, "E4", lambda: client.post("/v1/chat", headers=headers, json={**body, "question": ""}),
                 (422,), "empty question")
    expect_error(report, "E5", lambda: client.post("/v1/chat", headers=headers, json={**body, "question": "x" * 4001}),
                 (422,), "question over 4,000")
    expect_error(report, "E6", lambda: client.post("/v1/chat", headers=headers, json={**body, "collection": "zz-e2e-none"}),
                 (403, 404), "collection not allowed")
    expect_error(report, "E7", lambda: client.post("/v1/chat", headers=headers, json={**body, "conversation_id": "zz-e2e-none"}),
                 (404,), "unknown conversation")
    expect_error(report, "E8", lambda: client.get("/v1/conversations/zz-e2e-none/messages", headers=headers),
                 (404,), "read unknown conversation")
    if noscope_key:
        expect_error(report, "E9", lambda: client.post("/v1/chat", headers={**user, "ITI-Api-Key": noscope_key}, json=body),
                     (403,), "key without chat:invoke")
    else:
        print("E9   SKIP         key without chat:invoke ($env:ITI_CHAT_NOSCOPE_KEY not set)")


def part2_suggestions(client, report, headers, collection) -> None:
    print("\n-- Part 2: suggestions")
    response, seconds = timed(lambda: client.get("/v1/suggestions", headers=headers, params={"collection": collection}))
    ok = response.status_code == 200 and isinstance(response.json(), list)
    report.line("S1", ok, seconds, f"HTTP {response.status_code}, {len(response.json()) if ok else 0} suggestion(s)")


def part3_chat(client, report, headers, collection, doc_question) -> str | None:
    """Returns the documents conversation's id (for Part 5)."""
    print("\n-- Part 3: POST /v1/chat")
    response, seconds = timed(lambda: client.post("/v1/chat", headers=headers,
                                                  json={"question": doc_question, "collection": collection}))
    if response.status_code != 200:
        report.line("C1", False, seconds, f"documents question: HTTP {response.status_code} {code_of(response)}")
        return None
    body = response.json()
    paged = [f"{c['title']} p.{c['page']}" for c in body["citations"] if c.get("page")]
    report.line("C1", body["found"] and bool(paged), seconds, f"documents question: found={body['found']} cites {paged[:3]}")
    conversation_id = body["conversation_id"]

    response, seconds = timed(lambda: client.post("/v1/chat", headers=headers,
                                                  json={"question": OFF_TOPIC, "collection": collection}))
    if response.status_code != 200:
        report.line("C2", False, seconds, f"off-topic: HTTP {response.status_code} {code_of(response)}")
    else:
        off = response.json()
        report.line("C2", not off["found"] and not off["citations"], seconds,
                    f"off-topic (I don't know): found={off['found']} citations={len(off['citations'])}")

    response, seconds = timed(lambda: client.post("/v1/chat", headers=headers, json={
        "question": FOLLOW_UP, "collection": collection, "conversation_id": conversation_id}))
    if response.status_code != 200:
        report.line("C3", False, seconds, f"follow-up: HTTP {response.status_code} {code_of(response)}")
    else:
        same = response.json()["conversation_id"] == conversation_id
        report.line("C3", same, seconds, f"follow-up keeps the conversation: {same}")
    return conversation_id


def part4_stream(client, report, headers, collection, doc_question) -> str | None:
    """Returns the streamed conversation's id (for Part 5)."""
    print("\n-- Part 4: POST /v1/chat/stream")
    start = time.perf_counter()
    events, meta, done, error = [], {}, {}, {}
    with client.stream("POST", "/v1/chat/stream", headers=headers,
                       json={"question": doc_question, "collection": collection}) as response:
        if response.status_code != 200:
            response.read()
            report.line("T1", False, time.perf_counter() - start, f"HTTP {response.status_code} {code_of(response)}")
            return None
        event = ""
        for line in response.iter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
                if not events or events[-1] != event:
                    events.append(event)
                meta = data if event == "meta" else meta
                done = data if event == "done" else done
                error = data if event == "error" else error
    seconds = time.perf_counter() - start
    if error:
        report.line("T1", False, seconds, f"stream error {error.get('code')}")
        return None
    in_order = events == ["meta", "token", "done"]
    report.line("T1", in_order, seconds, f"events in order: {' -> '.join(events)}")
    shaped = {"answer", "found", "citations"} <= done.keys() and "conversation_id" in meta and "request_id" in meta
    report.line("T2", shaped, 0, f"meta has ids, done has answer/found/citations: {shaped} (found={done.get('found')})")
    return meta.get("conversation_id")


def part5_history(client, report, headers, conversation_ids: list[str]) -> None:
    print("\n-- Part 5: history")
    response, seconds = timed(lambda: client.get("/v1/conversations", headers=headers, params={"limit": 100}))
    listed = {c["conversation_id"] for c in response.json()} if response.status_code == 200 else set()
    report.line("H1", set(conversation_ids) <= listed, seconds, f"my list has this run's {len(conversation_ids)} conversation(s)")

    response, seconds = timed(lambda: client.get(f"/v1/conversations/{conversation_ids[0]}/messages", headers=headers))
    roles = [m["role"] for m in response.json()] if response.status_code == 200 else []
    alternating = roles[:4] == ["user", "assistant", "user", "assistant"]
    report.line("H2", alternating, seconds, f"messages: {len(roles)}, order user/assistant: {alternating}")

    other = {**headers, "ITI-User-Id": headers["ITI-User-Id"] + "-other"}
    response, seconds = timed(lambda: client.get(f"/v1/conversations/{conversation_ids[0]}/messages", headers=other))
    report.line("H3", response.status_code == 404, seconds,
                f"another user reads it: HTTP {response.status_code} {code_of(response)}")
    response, seconds = timed(lambda: client.get("/v1/conversations", headers=other, params={"limit": 100}))
    theirs = {c["conversation_id"] for c in response.json()} if response.status_code == 200 else set()
    report.line("H4", response.status_code == 200 and not theirs & set(conversation_ids), seconds,
                "another user's list does not show them")


def hr_verdict(report, check_id, wanted: tuple[str, ...], body: dict, seconds: float, label: str = "") -> bool:
    """PASS when every wanted tool is cited (built-in "hrdotnet:<tool>" or via MCP "<server>:hrdotnet__<tool>") and
    the answer is not empty. Prints tool names only, never the answer."""
    cited = sources(body)
    tools = [s.split(":", 1)[-1] for s in cited if ":" in s]
    ok = all(any(s.endswith(tool) for s in cited) for tool in wanted) and bool(body.get("answer", "").strip())
    return report.line(check_id, ok, seconds, f"{label}{'+'.join(wanted)}: cited {tools or 'documents'}")


def hr_ask(client, report, headers, collection, check_id, wanted, question, conversation_id=None, label=""):
    """One /v1/chat question; returns its conversation id (None when refused)."""
    body = {"question": question, "collection": collection, "conversation_id": conversation_id}
    response, seconds = timed(lambda: client.post("/v1/chat", headers=headers, json=body))
    if response.status_code != 200:
        report.line(check_id, False, seconds, f"{label}{'+'.join(wanted)}: HTTP {response.status_code} {code_of(response)}")
        return None
    hr_verdict(report, check_id, wanted, response.json(), seconds, label)
    return response.json()["conversation_id"]


def part6_hr(client, report, headers, collection) -> None:
    print(f"\n-- Part 6: HRDotNet tools as employee {headers['ITI-User-Id']} (answers not printed)")
    for check_id, wanted, question in HR_QUESTIONS:
        hr_ask(client, report, headers, collection, check_id, wanted, question)

    check_id, wanted, first, follow_up = HR_FOLLOW_UP
    conversation_id = hr_ask(client, report, headers, collection, check_id + "a", wanted, first)
    if conversation_id:
        same = hr_ask(client, report, headers, collection, check_id + "b", wanted, follow_up, conversation_id, "follow-up ")
        report.line(check_id + "c", same == conversation_id, 0, f"follow-up keeps the conversation: {same == conversation_id}")

    check_id, wanted, question = HR_STREAMED
    start = time.perf_counter()
    done, event = {}, ""
    with client.stream("POST", "/v1/chat/stream", headers=headers,
                       json={"question": question, "collection": collection}) as response:
        if response.status_code != 200:
            response.read()
            report.line(check_id, False, time.perf_counter() - start, f"streamed: HTTP {response.status_code} {code_of(response)}")
            return
        for line in response.iter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:") and event in ("done", "error"):
                done = json.loads(line[5:].strip()) | {"event": event}
    if done.get("event") != "done":
        report.line(check_id, False, time.perf_counter() - start, f"streamed: no done event ({done.get('code', '')})")
    else:
        hr_verdict(report, check_id, wanted, done, time.perf_counter() - start, "streamed ")


# --- Part 7: edge cases, checked against the real values (kept in memory, never printed) ---------------------------

PAYSLIPS_SQL = text("""
    SELECT period_from, period_to, gross_pay, net_pay FROM ai.v_payslips
    WHERE employee_id = :employee_id ORDER BY pay_date DESC, payslip_id DESC
""")
LEAVE_SQL = text("SELECT leave_name, remaining_days FROM ai.v_leave_balances WHERE employee_id = :employee_id AND year = :year")
EMPLOYEE_SQL = text("SELECT employee_no FROM ai.v_employment_info WHERE employee_id = :employee_id")
OVERTIME_SQL = text("SELECT document_no, ot_date FROM ai.v_overtime WHERE employee_id = :employee_id ORDER BY ot_date DESC")
TERMINATED_SQL = text("""
    SELECT TOP 1 e.employee_id FROM ai.v_employment_info AS e
    WHERE e.date_ended < GETDATE() AND (SELECT COUNT(*) FROM ai.v_payslips AS p WHERE p.employee_id = e.employee_id) >= 2
    ORDER BY e.date_ended DESC
""")
UNKNOWN_IDS = ("999999", "E-NOPE")
MONEY = re.compile(r"₱\s?\d|PHP\s?\d|(?<![\d.])\d{1,3}(?:,\d{3})+(?:\.\d{2})?(?!\d)|(?<![\d.])\d{4,}\.\d{2}(?!\d)")


def facts_of(conn, employee_id: str) -> dict:
    """One employee's values the checks look for. Never printed."""
    params = {"employee_id": employee_id}
    employee_no = conn.execute(EMPLOYEE_SQL, params).scalar()
    return {
        "payslips": [dict(row._mapping) for row in conn.execute(PAYSLIPS_SQL, params)],
        "leave": [dict(row._mapping) for row in conn.execute(LEAVE_SQL, {**params, "year": date.today().year})],
        "employee_no": str(employee_no).strip() if employee_no else "",
        "overtime": [dict(row._mapping) for row in conn.execute(OVERTIME_SQL, params)],
    }


def has_amount(answer: str, value) -> bool:
    """12,345.60 in the answer, with or without the comma."""
    return bool(re.search(rf"(?<![\d.]){re.escape(f'{Decimal(value):.2f}')}(?!\d)", answer.replace(",", "")))


def has_days(answer: str, value) -> bool:
    """7.00 as 7, 7.0 or 7.00; 7.50 as 7.5 or 7.50."""
    plain = format(Decimal(value).normalize(), "f")
    tail = "0*" if "." in plain else r"(?:\.0+)?"
    return bool(re.search(rf"(?<![\d.]){re.escape(plain)}{tail}(?!\.?\d)", answer))  # 7 must not be the start of 7.25


def has_text(answer: str, value: str) -> bool:
    return bool(value) and bool(re.search(rf"(?<![\w]){re.escape(value)}(?![\w])", answer, re.I))


def day(d: date) -> str:
    return f"{d:%B} {d.day}, {d.year}"


def month(d: date) -> str:
    return f"{d:%B %Y}"


def post(client, headers, collection, question):
    """(status, body or {}, seconds, error code)."""
    response, seconds = timed(lambda: client.post("/v1/chat", headers=headers, json={"question": question, "collection": collection}))
    if response.status_code != 200:
        return response.status_code, {}, seconds, code_of(response)
    return 200, response.json(), seconds, ""


def tools_in(body: dict) -> list[str]:
    return [s.split(":", 1)[-1] for s in sources(body) if ":" in s]


def edge_line(report, check_id, status, body, seconds, code, ok: bool, why: str) -> None:
    if status != 200:
        report.line(check_id, False, seconds, f"{why.split(':')[0]}: HTTP {status} {code}")
    else:
        report.line(check_id, ok, seconds, f"{why}; cited {tools_in(body) or [c for c in sources(body)][:2] or 'nothing'}")


def part7_values(client, report, headers, collection, mine) -> None:
    print("\n-- Part 7A: the values are right (counts only)")
    latest = mine["payslips"][0] if mine["payslips"] else None
    if latest:
        status, body, seconds, code = post(client, headers, collection, "Show my latest payslip.")
        ok = has_amount(body.get("answer", ""), latest["net_pay"])
        edge_line(report, "V1", status, body, seconds, code, ok, f"latest net pay present: {ok}")
    q4 = [p for p in mine["payslips"] if p["period_from"] <= date(2025, 12, 31) and p["period_to"] >= date(2025, 10, 1)]
    if q4:
        status, body, seconds, code = post(client, headers, collection,
                                           "Show my payslips for October to December 2025 with the gross and net pay.")
        answer = body.get("answer", "")
        nets = sum(has_amount(answer, p["net_pay"]) for p in q4)
        grosses = sum(has_amount(answer, p["gross_pay"]) for p in q4)
        edge_line(report, "V2", status, body, seconds, code, nets == grosses == len(q4),
                  f"net {nets}/{len(q4)}, gross {grosses}/{len(q4)}")
    if mine["leave"]:
        status, body, seconds, code = post(client, headers, collection,
                                           "How many leave credits do I have left this year, per leave type?")
        hits = sum(has_days(body.get("answer", ""), row["remaining_days"]) for row in mine["leave"])
        edge_line(report, "V3", status, body, seconds, code, hits == len(mine["leave"]),
                  f"remaining days {hits}/{len(mine['leave'])} leave types")
    if mine["employee_no"]:
        status, body, seconds, code = post(client, headers, collection, "What is my employee number and position?")
        ok = has_text(body.get("answer", ""), mine["employee_no"])
        edge_line(report, "V4", status, body, seconds, code, ok, f"employee number present: {ok}")
    if mine["overtime"]:
        end = mine["overtime"][0]["ot_date"]
        start = end - timedelta(days=29)
        wanted = {str(r["document_no"]).strip() for r in mine["overtime"] if start <= r["ot_date"] <= end and r["document_no"]}
        status, body, seconds, code = post(client, headers, collection,
                                           f"Show my overtime applications from {day(start)} to {day(end)} with their document numbers.")
        hits = sum(has_text(body.get("answer", ""), number) for number in wanted)
        edge_line(report, "V5", status, body, seconds, code, hits == len(wanted), f"document numbers {hits}/{len(wanted)}")


def no_figures(body: dict) -> bool:
    return not MONEY.search(body.get("answer", ""))


def part7_no_data(client, report, headers, collection, mine) -> None:
    print("\n-- Part 7B: no data, nothing invented")
    if mine["payslips"]:
        earliest = min(p["period_from"] for p in mine["payslips"])
        empty_month = (earliest.replace(day=1) - timedelta(days=1)).replace(day=1)
        status, body, seconds, code = post(client, headers, collection, f"Show my payslips for {month(empty_month)}.")
        ok = no_figures(body)
        edge_line(report, "N1", status, body, seconds, code, ok, f"month with no payslip: no peso amount {ok}, found={body.get('found')}")
    days = {r["ot_date"] for r in mine["overtime"]}
    end = date.today()
    for _ in range(24):  # the first 30 days back from today with no overtime filed
        if not any(end - timedelta(days=29) <= d <= end for d in days):
            break
        end -= timedelta(days=30)
    status, body, seconds, code = post(client, headers, collection,
                                       f"Show my overtime applications from {day(end - timedelta(days=29))} to {day(end)}.")
    ok = not any(has_text(body.get("answer", ""), str(r["document_no"]).strip()) for r in mine["overtime"] if r["document_no"])
    edge_line(report, "N2", status, body, seconds, code, ok, f"30 days with no overtime: no document number {ok}")
    status, body, seconds, code = post(client, headers, collection, "Show my payslip for December 2027.")
    ok = no_figures(body)
    edge_line(report, "N3", status, body, seconds, code, ok, f"future payslip: no peso amount {ok}, found={body.get('found')}")


def part7_ranges(client, report, headers, collection) -> None:
    print("\n-- Part 7C: out-of-range periods (a sane reply, no 500)")
    questions = [
        ("P1", "Was I late or absent at any time in 2025? Give me the totals for the whole year."),
        ("P2", "What is my work schedule for the next 3 months?"),
        ("P3", "Show my clock punches from October 20 to October 1, 2026."),
    ]
    for check_id, question in questions:
        status, body, seconds, code = post(client, headers, collection, question)
        ok = bool(body.get("answer", "").strip())
        edge_line(report, check_id, status, body, seconds, code, ok, f"answered: {ok}, found={body.get('found')}")


def part7_unknown(client, report, headers, collection, mine) -> None:
    print("\n-- Part 7D: unknown employee ids")
    known = [p["net_pay"] for p in mine["payslips"]] + [p["gross_pay"] for p in mine["payslips"]]
    checks = [("U1", UNKNOWN_IDS[0], "Show my latest payslip."),
              ("U2", UNKNOWN_IDS[0], "What is my employee number?"),
              ("U3", UNKNOWN_IDS[1], "Show my latest payslip.")]
    for check_id, user_id, question in checks:
        status, body, seconds, code = post(client, {**headers, "ITI-User-Id": user_id}, collection, question)
        answer = body.get("answer", "")
        clean = no_figures(body) and not any(has_amount(answer, v) for v in known if v) \
            and not has_text(answer, mine["employee_no"])
        edge_line(report, check_id, status, body, seconds, code, clean, f"id {user_id}: nothing of anyone's: {clean}")


def part7_terminated(client, report, headers, collection, conn) -> None:
    print("\n-- Part 7E: a terminated employee (only the latest posted payslip)")
    leaver = conn.execute(TERMINATED_SQL).scalar()
    if not leaver:
        print("K    SKIP         no terminated employee with 2+ payslips")
        return
    theirs = facts_of(conn, str(leaver))
    as_leaver = {**headers, "ITI-User-Id": str(leaver)}
    latest = theirs["payslips"][0]
    status, body, seconds, code = post(client, as_leaver, collection, "Show my latest payslip.")
    ok = has_amount(body.get("answer", ""), latest["net_pay"])
    edge_line(report, "K1", status, body, seconds, code, ok, f"latest payslip given: {ok}")
    older = next((p for p in theirs["payslips"][1:] if p["net_pay"] != latest["net_pay"]), None)
    if older:
        status, body, seconds, code = post(client, as_leaver, collection,
                                           f"Show my payslips for {month(older['period_from'])}.")
        answer = body.get("answer", "")
        ok = not any(has_amount(answer, p["net_pay"]) for p in theirs["payslips"][1:] if p["net_pay"] != latest["net_pay"])
        edge_line(report, "K2", status, body, seconds, code, ok, f"older payslip withheld: {ok}")
    status, body, seconds, code = post(client, as_leaver, collection, "How many leave credits do I have left?")
    others = [t for t in tools_in(body) if not t.endswith("get_my_payslip")]
    edge_line(report, "K3", status, body, seconds, code, not others, f"other HR tools refused: {not others}")


def part7_mixed(client, report, headers, collection) -> None:
    print("\n-- Part 7F: a policy AND own-records question (must cite both)")
    checks = [("M1", "get_my_overtime", "What does the company policy say about overtime, and how much overtime did I "
                                        "file in the last 30 days?"),
              ("M2", "get_my_leave_credits", "What is the company rule on sick leave, and how many sick leave credits "
                                             "do I have left?")]
    for check_id, tool, question in checks:
        status, body, seconds, code = post(client, headers, collection, question)
        document = any(":" not in s for s in sources(body))
        records = any(s.endswith(tool) for s in sources(body))
        edge_line(report, check_id, status, body, seconds, code, document and records,
                  f"document cited: {document}, {tool} cited: {records}")


def part7_edges(client, report, headers, collection) -> None:
    with get_hrdotnet_engine().connect() as conn:
        mine = facts_of(conn, headers["ITI-User-Id"])
        part7_values(client, report, headers, collection, mine)
        part7_no_data(client, report, headers, collection, mine)
        part7_ranges(client, report, headers, collection)
        part7_unknown(client, report, headers, collection, mine)
        part7_terminated(client, report, headers, collection, conn)
    part7_mixed(client, report, headers, collection)


def hr_down(client, report, headers, collection) -> None:
    print("\n-- HR database down (run only while the console points HRDotNet at an unreachable address)")
    with get_hrdotnet_engine().connect() as conn:  # the script's own connection still uses ITI_HRDOTNET_DB_URL
        mine = facts_of(conn, headers["ITI-User-Id"])
    known = [p["net_pay"] for p in mine["payslips"]] + [r["remaining_days"] for r in mine["leave"]]
    for check_id, question in (("D1", "Show my latest payslip."), ("D2", "How many leave credits do I have left this year?")):
        status, body, seconds, code = post(client, headers, collection, question)
        if status == 503:
            report.line(check_id, True, seconds, f"HTTP 503 {code}")
            continue
        answer = body.get("answer", "")
        clean = no_figures(body) and not tools_in(body) and not any(has_amount(answer, v) for v in known if v)
        edge_line(report, check_id, status, body, seconds, code, clean, f"clean reply, no figures: {clean}")


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end smoke test of every chat route.")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--collection", default="iti-docs")
    parser.add_argument("--user", default="chat-e2e", help="the ITI-User-Id for Parts 1-5 (its chats show under it)")
    parser.add_argument("--question", default="How do I file a vacation leave request?",
                        help="a question the collection's documents answer")
    parser.add_argument("--hr-user", default="10", help="the HRDotNet employee id Part 6 asks as (default 10)")
    parser.add_argument("--no-hr", action="store_true", help="skip Parts 6-7 (a key without the hrdotnet tools)")
    parser.add_argument("--no-edge", action="store_true", help="skip Part 7 (the edge cases)")
    parser.add_argument("--hr-down", action="store_true", help="run ONLY the HR-database-down checks (see the runbook)")
    args = parser.parse_args()
    key = os.environ.get("ITI_CHAT_CHECK_KEY")
    if not key:
        raise SystemExit("Set $env:ITI_CHAT_CHECK_KEY to a key with chat:invoke (see the docstring).")
    sys.stdout.reconfigure(encoding="utf-8")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # importing app/ turns its logging on: keep one line per check
    report = Report()
    headers = {"ITI-Api-Key": key, "ITI-User-Id": args.user}
    if args.hr_down:
        with httpx.Client(base_url=args.url, timeout=300) as client:
            hr_down(client, report, {**headers, "ITI-User-Id": args.hr_user}, args.collection)
        print(f"\n{report.passed}/{report.passed + report.failed} passed")
        raise SystemExit(0 if report.failed == 0 else 1)
    with httpx.Client(base_url=args.url, timeout=300) as client:
        part1_refused(client, report, headers, args.collection, os.environ.get("ITI_CHAT_NOSCOPE_KEY"))
        part2_suggestions(client, report, headers, args.collection)
        conversation_ids = [part3_chat(client, report, headers, args.collection, args.question),
                            part4_stream(client, report, headers, args.collection, args.question)]
        conversation_ids = [c for c in conversation_ids if c]
        if conversation_ids:
            part5_history(client, report, headers, conversation_ids)
        else:
            print("\n-- Part 5: skipped (no conversation was created)")
        if not args.no_hr:
            part6_hr(client, report, {**headers, "ITI-User-Id": args.hr_user}, args.collection)
            if not args.no_edge:
                part7_edges(client, report, {**headers, "ITI-User-Id": args.hr_user}, args.collection)
    print(f"\n{report.passed}/{report.passed + report.failed} passed")
    raise SystemExit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
