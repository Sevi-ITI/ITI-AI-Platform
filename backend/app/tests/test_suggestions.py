"""GET /v1/suggestions: starter questions (chips) for a new chat, one per indexed file, picked at random."""

import pytest

from app.documents.d_service.title_of import title_of

FILES = ("Leave Policy.pdf", "ITI_Code-of_Discipline.pdf", "LaborCodePH2017.pdf", "Dress Code.pdf")


@pytest.fixture
def uploaded(client, make_key):
    """Indexes FILES in iti-docs (the fake rag reads a "PDF" as plain text) and returns a chat-only key."""
    writer = make_key("hr-portal", scopes=["documents:write"])
    for name in FILES:
        r = client.post("/v1/documents", headers=writer, data={"collection": "iti-docs"},
                        files={"file": (name, b"page one", "application/pdf")})
        assert r.status_code == 202, r.text
    return make_key("hr-portal")


def test_titles_follow_the_console_rule():
    assert title_of("ITI_Code-of_Discipline.pdf") == "ITI Code of Discipline"
    assert title_of("LaborCodePH2017.pdf") == "Labor Code PH 2017"
    assert title_of("Leave Policy.PDF") == "Leave Policy"


def test_titles_drop_the_ocr_and_word_tags():
    assert title_of("travel time policy (OCR).pdf") == "travel time policy"
    assert title_of("Request for Payment (Word).pdf") == "Request for Payment"
    assert title_of("Dress Code (ocr) rev 2.pdf") == "Dress Code rev 2"
    assert title_of("Memo (Draft).pdf") == "Memo (Draft)"  # only those two tags


def test_up_to_three_chips_one_per_file_from_the_indexed_files(client, uploaded):
    r = client.get("/v1/suggestions", headers=uploaded, params={"collection": "iti-docs"})
    chips = r.json()
    assert r.status_code == 200 and len(chips) == 3
    assert len({c["file"] for c in chips}) == 3 and {c["file"] for c in chips} <= set(FILES)
    assert all(c["question"] == f"What does {title_of(c['file'])} cover?" for c in chips)


def test_the_pick_changes_and_limit_caps_it(client, uploaded):
    seen = set()
    for _ in range(20):
        chips = client.get("/v1/suggestions", headers=uploaded, params={"collection": "iti-docs", "limit": 2}).json()
        assert len(chips) == 2
        seen |= {c["file"] for c in chips}
    assert len(seen) > 2  # random, not always the same two
    all_files = client.get("/v1/suggestions", headers=uploaded, params={"collection": "iti-docs", "limit": 6}).json()
    assert sorted(c["file"] for c in all_files) == sorted(FILES)  # fewer files than the limit: all of them


def test_no_files_yet_is_an_empty_list(client, make_key):
    r = client.get("/v1/suggestions", headers=make_key("hr-portal"), params={"collection": "iti-docs"})
    assert r.status_code == 200 and r.json() == []


@pytest.mark.parametrize("params, status, code", [
    ({"collection": "iti-docs", "limit": 7}, 422, "invalid_request"),
    ({}, 422, "invalid_request"),
])
def test_bad_queries_are_422(client, make_key, params, status, code):
    r = client.get("/v1/suggestions", headers=make_key("hr-portal"), params=params)
    assert r.status_code == status and r.json()["error"]["code"] == code


def test_same_key_rules_as_chat(client, make_key, make_collection):
    make_collection("finance")
    assert client.get("/v1/suggestions", params={"collection": "iti-docs"}).status_code == 401
    no_chat = make_key("hr-portal", scopes=["documents:write"])
    r = client.get("/v1/suggestions", headers=no_chat, params={"collection": "iti-docs"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "scope_forbidden"
    r = client.get("/v1/suggestions", headers=make_key("hr-portal"), params={"collection": "finance"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "collection_forbidden"
