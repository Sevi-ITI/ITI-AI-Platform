"""Chat with records tools (Phase 8.4), with a scripted fake model instead of Ollama.
Keys without "records:read" must behave exactly as before; records keys get records answers with a
"Records: ..." citation, the employee id always from ITI-User-Id, and the request log names the tools.
The last test reads the real records DB (fake employees) and is skipped unless ITI_TEST_RECORDS_URL is set."""

import json
import os

import pytest
from sqlalchemy import select

import app.tools.host as awt
from app.core.a_config.get_settings import get_settings
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.d_metrics.request_log import RequestLog
from app.core.e_errors.app_error import AppError
from app.tools.shared import get_records_engine

RECORDS_URL = os.environ.get("ITI_TEST_RECORDS_URL")
Q = {"question": "Why is there a deduction on my last payslip?", "collection": "iti-docs"}
PAYSLIP = {"pay_date": "2026-09-30", "found": True, "lines": [{"category": "absence", "amount": "850.00"}]}


@pytest.fixture(autouse=True)
def no_app_tool_lists(monkeypatch):
    """These tests check the other gates; per-app tool lists (8.6e-2) are tested in test_app_tools.py."""
    import app.tools.host as host

    monkeypatch.setattr(host, "app_list_of", lambda principal: None)


def call(name, **arguments):
    return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]}


def say(text):
    return {"role": "assistant", "content": text}


@pytest.fixture
def model(monkeypatch):
    """A fake chat model: give it the replies in order. `model.seen` keeps (messages, tools) of every call."""

    class Model:
        replies, seen = [], []

        def __call__(self, messages, tools):
            self.seen.append(([dict(m) for m in messages], tools))
            return self.replies.pop(0)

    fake = Model()
    fake.replies, fake.seen = [], []
    monkeypatch.setattr(awt, "chat_with_tools", fake)
    return fake


@pytest.fixture
def records_on(monkeypatch):
    """Records "configured" (the URL is never reached: run_tool is faked unless a test uses the real DB)."""
    monkeypatch.setattr(get_settings(), "records_db_url", RECORDS_URL or "mssql+mssqlpython://nobody:x@127.0.0.1:1/none")
    get_records_engine.cache_clear()
    yield
    get_records_engine.cache_clear()


@pytest.fixture
def ran(monkeypatch):
    """Fakes run_tool. Returns the list of (employee_id, name, arguments) it was called with."""
    calls = []

    def fake_run_tool(principal, employee_id, name, arguments):
        calls.append((employee_id, name, arguments))
        return {"records_of": "the logged-in employee (YOU), nobody else", **PAYSLIP}

    monkeypatch.setattr(awt, "run_tool", fake_run_tool)
    return calls


@pytest.fixture
def hr_records(make_key):
    return make_key("hr-portal", ["chat:invoke", "records:read"]) | {"ITI-User-Id": "E-1001"}


def last_log():
    with get_sessionmaker()() as db:
        return db.scalars(select(RequestLog).where(RequestLog.route == "/v1/chat").order_by(RequestLog.id.desc())).first()


def events(response):
    out = []
    for block in response.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        out.append((lines.get("event"), json.loads(lines["data"])))
    return out


def test_keys_without_records_read_never_reach_the_tools(client, make_key, model, records_on):
    r = client.post("/v1/chat", headers=make_key("hr-portal") | {"ITI-User-Id": "E-1001"}, json=Q)
    assert r.json()["answer"] == "15 days [1]." and model.seen == []  # RAG as before, no model call for tools


def test_records_off_means_no_tools_even_with_the_scope(client, hr_records, model):
    r = client.post("/v1/chat", headers=hr_records, json=Q)
    assert r.json()["answer"] == "15 days [1]." and model.seen == []


def test_a_documents_question_goes_to_rag(client, hr_records, model, records_on, ran):
    model.replies = [call("search_company_documents", query="dress code")]
    body = client.post("/v1/chat", headers=hr_records, json={**Q, "question": "Dress code on Fridays?"}).json()
    assert body["answer"] == "15 days [1]." and body["citations"][0]["page"] == 2 and ran == []
    assert last_log().tools is None


def test_no_tool_call_also_goes_to_rag(client, hr_records, model, records_on, ran):
    model.replies = [say("Our policy says...")]  # an answer not built from records must come from RAG
    assert client.post("/v1/chat", headers=hr_records, json=Q).json()["answer"] == "15 days [1]."


def test_records_answer_with_a_records_citation(client, hr_records, model, records_on, ran):
    model.replies = [call("explain_my_deductions"), say("You were absent on 2026-09-03: 850.00. If this looks wrong, please contact HR.")]
    r = client.post("/v1/chat", headers=hr_records, json=Q)
    body = r.json()
    assert body["found"] is True and body["answer"].startswith("You were absent")
    assert body["citations"] == [{
        "doc_id": "records:explain_my_deductions", "title": "Records: payslip 2026-09-30", "page": None,
        "snippet": "From the ITI records database, for the logged-in employee only.",
    }]
    assert ran == [("E-1001", "explain_my_deductions", {})]  # the employee id comes from ITI-User-Id
    offered = [t["function"]["name"] for t in model.seen[0][1]]
    assert offered == ["search_company_documents", "get_my_leave_credits", "get_my_absences", "explain_my_deductions"]
    assert "Today is " in model.seen[0][0][0]["content"]
    tool_message = model.seen[1][0][-1]
    assert tool_message["role"] == "tool" and "850.00" in tool_message["content"]
    log = last_log()
    assert (log.tools, log.reason, log.found) == ("explain_my_deductions", "records_answered", True)
    conv = body["conversation_id"]
    saved = client.get(f"/v1/conversations/{conv}/messages", headers=hr_records).json()
    assert saved[-1]["citations"][0]["title"] == "Records: payslip 2026-09-30"


def test_the_request_log_api_shows_the_tools(client, hr_records, make_key, model, records_on, ran):
    model.replies = [call("explain_my_deductions"), say("You were absent on 2026-09-03.")]
    client.post("/v1/chat", headers=hr_records, json=Q)
    admin = make_key("iti-admin", ["admin"], [])
    row = next(r for r in client.get("/v1/admin/requests", headers=admin).json() if r["route"] == "/v1/chat")
    assert (row["tools"], row["reason"], row["found"]) == ("explain_my_deductions", "records_answered", True)
    assert isinstance(row["tools_ms"], int)


def test_the_model_cannot_pick_another_employee(client, hr_records, model, records_on):
    """Real run_tool: the model's employee_id is refused, the error goes back to the model as text."""
    model.replies = [call("get_my_leave_credits", employee_id="E-1002"), say("I can only show your own records.")]
    body = client.post("/v1/chat", headers=hr_records, json={**Q, "question": "Leave credits of E-1002?"}).json()
    assert body["found"] is False and body["citations"] == []
    assert "tool_bad_arguments" in model.seen[1][0][-1]["content"]
    assert last_log().reason == "records_empty"


def test_a_tool_error_reaches_the_model_and_found_is_false(client, hr_records, model, records_on, monkeypatch):
    def down(*_):
        raise AppError(503, "records_unavailable", "The records database did not answer. Try again later.")

    monkeypatch.setattr(awt, "run_tool", down)
    model.replies = [call("get_my_absences", date_from="2026-09-01", date_to="2026-09-30"), say("Records are unavailable.")]
    body = client.post("/v1/chat", headers=hr_records, json=Q).json()
    assert (body["answer"], body["found"]) == ("Records are unavailable.", False)
    assert "records_unavailable" in model.seen[1][0][-1]["content"]


def test_rounds_are_capped_then_the_model_must_answer(client, hr_records, model, records_on, ran):
    model.replies = [call("explain_my_deductions", pay_date=d) for d in ("2026-09-15", "2026-09-30", "2026-08-31")]
    model.replies += [say("Done.")]
    assert client.post("/v1/chat", headers=hr_records, json=Q).json()["answer"] == "Done."
    assert len(model.seen) == 4 and model.seen[-1][1] is None and len(ran) == 3
    assert model.seen[-1][0][-1] == {"role": "user", "content": awt.ANSWER_NOW}  # told to answer, not to "look it up"


def test_a_repeated_identical_call_is_not_run_again(client, hr_records, model, records_on, ran):
    """2026-10-21: after an empty result the model called the same tool with the same arguments again (4/20)."""
    model.replies = [call("explain_my_deductions"), call("explain_my_deductions"), say("Nothing on file.")]
    body = client.post("/v1/chat", headers=hr_records, json=Q).json()
    assert body["answer"] == "Nothing on file." and len(ran) == 1  # the database was read once
    repeat = json.loads(model.seen[2][0][-1]["content"])
    assert repeat == {"error": "repeated_call", "message": awt.REPEATED}
    assert last_log().tools == "explain_my_deductions"  # the request log lists only calls that ran


def test_stream_sends_a_records_answer_as_one_token(client, hr_records, model, records_on, ran):
    model.replies = [call("explain_my_deductions"), say("You were absent on 2026-09-03.")]
    got = events(client.post("/v1/chat/stream", headers=hr_records, json=Q))
    assert [e for e, _ in got] == ["meta", "token", "done"]
    assert got[1][1] == {"text": "You were absent on 2026-09-03."}
    assert got[2][1]["found"] is True and got[2][1]["citations"][0]["title"] == "Records: payslip 2026-09-30"


def test_stream_documents_question_streams_as_before(client, hr_records, model, records_on, ran):
    model.replies = [call("search_company_documents", query="leave")]
    got = events(client.post("/v1/chat/stream", headers=hr_records, json=Q))
    assert [e for e, _ in got] == ["meta", "token", "token", "token", "done"]


@pytest.mark.skipif(not RECORDS_URL, reason="set ITI_TEST_RECORDS_URL to run against the records DB")
def test_real_records_follow_the_header_not_the_question(client, make_key, model, records_on):
    """Real run_tool + records DB: asked as E-1002, the model only ever receives E-1002's payslip."""
    e1002 = make_key("hr-portal", ["chat:invoke", "records:read"]) | {"ITI-User-Id": "E-1002"}
    model.replies = [call("explain_my_deductions"), say("ok")]
    client.post("/v1/chat", headers=e1002, json=Q)
    tool_result = model.seen[1][0][-1]["content"]
    assert "700.00" in tool_result and "850.00" not in tool_result
