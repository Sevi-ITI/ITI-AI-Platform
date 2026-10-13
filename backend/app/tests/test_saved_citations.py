"""6A.2: an answer's citations are saved with it and come back in both history views."""

Q = {"question": "How many vacation days?", "collection": "iti-docs"}
CITATION = {"doc_id": "Leave Policy.pdf", "title": "Leave Policy.pdf", "page": 2, "snippet": "Regular employees get 15 days."}


def test_citations_are_saved_with_the_answer_for_both_json_and_stream(client, make_key):
    hr = make_key("hr-portal") | {"ITI-User-Id": "1042"}
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    conv = client.post("/v1/chat", headers=hr, json=Q).json()["conversation_id"]
    client.post("/v1/chat/stream", headers=hr, json=Q | {"conversation_id": conv})
    client.post("/v1/chat", headers=hr, json=Q | {"question": "unknown thing", "conversation_id": conv})

    mine = client.get(f"/v1/conversations/{conv}/messages", headers=hr).json()
    assert [m["citations"] for m in mine] == [None, [CITATION], None, [CITATION], None, []]
    reviewed = client.get(f"/v1/admin/conversations/{conv}/messages", headers=admin).json()
    assert [m["citations"] for m in reviewed] == [m["citations"] for m in mine]
