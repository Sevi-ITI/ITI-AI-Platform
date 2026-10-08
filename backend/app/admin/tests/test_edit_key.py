"""6A.5: a key's collections and expiry can be edited; nothing else, and never a revoked key."""

from datetime import UTC, datetime, timedelta

Q = {"question": "How many vacation days?", "collection": "finance-docs"}


def test_edit_collections_and_expiry(client, make_key):
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    hr = make_key("hr-portal") | {"ITI-User-Id": "1042"}
    key_id = next(k["key_id"] for k in client.get("/v1/admin/keys", headers=admin).json() if k["app_id"] == "hr-portal")
    assert client.post("/v1/chat", headers=hr, json=Q).json()["error"]["code"] == "collection_forbidden"

    edited = client.patch(f"/v1/admin/keys/{key_id}", headers=admin, json={"allowed_collections": ["iti-docs", "finance-docs"]})
    assert edited.status_code == 200 and edited.json()["allowed_collections"] == ["iti-docs", "finance-docs"]
    assert edited.json()["scopes"] == ["chat:invoke"]  # unchanged
    # takes effect at once: the key may now ask about finance-docs (which this test setup has no store for)
    assert client.post("/v1/chat", headers=hr, json=Q).json()["error"]["code"] == "collection_not_found"

    days = client.patch(f"/v1/admin/keys/{key_id}", headers=admin, json={"valid_days": 30}).json()["expires_at"]
    left = datetime.fromisoformat(days.replace("Z", "+00:00")) - datetime.now(UTC)
    assert timedelta(days=29) < left <= timedelta(days=30)
    assert client.patch(f"/v1/admin/keys/{key_id}", headers=admin, json={"valid_days": None}).json()["expires_at"] is None
    ignored = client.patch(f"/v1/admin/keys/{key_id}", headers=admin, json={"scopes": ["admin"]})
    assert ignored.json()["scopes"] == ["chat:invoke"]  # scopes are not editable: rotate the key instead

    client.delete(f"/v1/admin/keys/{key_id}", headers=admin)
    revoked = client.patch(f"/v1/admin/keys/{key_id}", headers=admin, json={"valid_days": 30})
    assert revoked.status_code == 409 and revoked.json()["error"]["code"] == "key_revoked"
    assert client.patch("/v1/admin/keys/000000000000", headers=admin, json={}).status_code == 404
