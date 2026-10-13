"""6A.3: the optional ITI-User-Role label is recorded (lowercased) and the user list shows the latest one."""

Q = {"question": "How many vacation days?", "collection": "iti-docs"}


def test_the_latest_role_label_is_shown_and_it_changes_nothing_else(client, make_key):
    hr = make_key("hr-portal")
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    client.post("/v1/chat", headers=hr | {"ITI-User-Id": "1042", "ITI-User-Role": " Staff "}, json=Q)
    client.post("/v1/chat", headers=hr | {"ITI-User-Id": "1042", "ITI-User-Role": "HR Manager"}, json=Q)
    client.post("/v1/chat", headers=hr | {"ITI-User-Id": "1042"}, json=Q)  # no label this time: the latest stays
    client.post("/v1/chat", headers=hr | {"ITI-User-Id": "2210"}, json=Q)

    users = {u["user_id"]: u["user_role"] for u in client.get("/v1/admin/users", headers=admin).json()}
    assert users == {"1042": "hr manager", "2210": None}
    log = client.get("/v1/admin/requests", headers=admin).json()
    assert [r["user_role"] for r in log] == [None, None, "hr manager", "staff"]
    too_long = client.post("/v1/chat", headers=hr | {"ITI-User-Id": "1042", "ITI-User-Role": "x" * 51}, json=Q)
    assert too_long.status_code == 422
