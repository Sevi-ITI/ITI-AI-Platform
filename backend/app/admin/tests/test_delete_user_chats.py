"""6A.4: the super admin erases one user's chats in one app; nobody else's are touched."""

Q = {"question": "How many vacation days?", "collection": "iti-docs"}


def test_erase_one_users_chats_in_one_app(client, make_key):
    hr, other = make_key("hr-portal"), make_key("finance-app")
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    for headers in (hr | {"ITI-User-Id": "1042"}, hr | {"ITI-User-Id": "1042"}, hr | {"ITI-User-Id": "2210"}):
        client.post("/v1/chat", headers=headers, json=Q)
    client.post("/v1/chat", headers=other | {"ITI-User-Id": "1042"}, json=Q)  # same id, another app: kept

    r = client.delete("/v1/admin/conversations", headers=admin, params={"app_id": "hr-portal", "user_id": "1042"})
    assert r.status_code == 200
    assert r.json() == {"app_id": "hr-portal", "user_id": "1042", "conversations": 2, "messages": 4}
    left = [(c["app_id"], c["user_id"]) for c in client.get("/v1/admin/conversations", headers=admin).json()]
    assert sorted(left) == [("finance-app", "1042"), ("hr-portal", "2210")]
    assert client.get("/v1/conversations", headers=hr | {"ITI-User-Id": "1042"}).json() == []

    again = client.delete("/v1/admin/conversations", headers=admin, params={"app_id": "hr-portal", "user_id": "1042"})
    assert again.json()["conversations"] == 0
    assert client.delete("/v1/admin/conversations", headers=admin, params={"app_id": "hr-portal"}).status_code == 422
