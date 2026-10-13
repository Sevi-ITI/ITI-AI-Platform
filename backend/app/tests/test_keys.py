"""API keys: the key format, hashing, expiry/revocation, and the 401/403 a caller gets."""

from datetime import UTC, datetime, timedelta

from app.auth.d_keys.generate_key import generate_key
from app.auth.d_keys.hash_secret import hash_secret
from app.auth.d_keys.is_active import is_active
from app.auth.d_keys.secret_matches import secret_matches
from app.auth.d_keys.split_key import split_key

CHAT = {"question": "How many vacation days?", "collection": "iti-docs"}


def test_a_new_key_splits_back_into_its_id_and_secret_and_only_the_hash_is_kept():
    key_id, full_key, secret_hash = generate_key()
    assert full_key.startswith("iti_sk_") and len(key_id) == 12
    assert split_key(full_key) == (key_id, full_key.split("_", 3)[3])
    assert secret_matches(split_key(full_key)[1], secret_hash) and full_key not in secret_hash
    assert secret_hash == hash_secret(split_key(full_key)[1])


def test_malformed_keys_are_rejected_before_any_database_lookup():
    for raw in [
        "",
        "Bearer x",
        "iti_sk_",
        "iti_sk_short_secret",
        "iti_pk_3f9a1c2b7e4d_secret",
        " iti_sk_3f9a1c2b7e4d_x",
    ]:
        assert split_key(raw) is None


def test_revoked_or_expired_keys_are_inactive_including_sqlite_naive_datetimes():
    now = datetime.now(UTC)
    assert is_active(None, None) and is_active(None, now + timedelta(days=1))
    assert not is_active(now, None)
    assert not is_active(None, now - timedelta(seconds=1))
    assert not is_active(None, (now - timedelta(days=1)).replace(tzinfo=None))


def test_missing_wrong_and_revoked_keys_get_the_same_401(client, make_key):
    good = make_key("hr-portal")
    wrong = {"ITI-Api-Key": good["ITI-Api-Key"][:-2] + "xx"}
    for headers in ({}, {"ITI-Api-Key": "not-a-key"}, wrong):
        r = client.post("/v1/chat", headers=headers | {"ITI-User-Id": "1042"}, json=CHAT)
        assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_api_key"


def test_expired_key_gets_401(client, make_key, db_engine):
    from app.auth.b_models.api_key import ApiKey
    from app.core.c_database.get_sessionmaker import get_sessionmaker

    headers = make_key("hr-portal")
    with get_sessionmaker()() as db:
        row = db.get(ApiKey, split_key(headers["ITI-Api-Key"])[0])
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    r = client.post("/v1/chat", headers=headers | {"ITI-User-Id": "1042"}, json=CHAT)
    assert r.status_code == 401


def test_a_key_without_the_scope_or_the_collection_gets_403(client, make_key, make_collection):
    make_collection("finance")
    docs_only = make_key("uploader", scopes=["documents:write"])
    finance = make_key("finance-app", collections=["finance"])
    r = client.post("/v1/chat", headers=docs_only | {"ITI-User-Id": "1042"}, json=CHAT)
    assert r.status_code == 403 and r.json()["error"]["code"] == "scope_forbidden"
    r = client.post("/v1/chat", headers=finance | {"ITI-User-Id": "1042"}, json=CHAT)
    assert r.status_code == 403 and r.json()["error"]["code"] == "collection_forbidden"
