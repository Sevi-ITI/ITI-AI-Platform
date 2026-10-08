"""6A.6: apps with documents:write can delete a file, with the same rules as the admin delete."""

from pathlib import Path

FILES = {"file": ("Old Policy.pdf", b"page one|page two", "application/pdf")}
WHERE = {"collection": "iti-docs", "filename": "Old Policy.pdf"}


def test_an_app_deletes_its_document(client, make_key):
    from app.core.a_config.get_settings import get_settings

    hr = make_key("hr-portal", scopes=["documents:write"])
    client.post("/v1/documents", headers=hr, data={"collection": "iti-docs"}, files=FILES)
    stored = Path(get_settings().upload_dir) / "iti-docs" / "Old Policy.pdf"
    assert stored.exists()

    assert client.delete("/v1/documents", headers=make_key("chat-only"), params=WHERE).status_code == 403
    other = make_key("finance-app", scopes=["documents:write"], collections=["finance-docs"])
    assert client.delete("/v1/documents", headers=other, params=WHERE).json()["error"]["code"] == "collection_forbidden"

    assert client.delete("/v1/documents", headers=hr, params=WHERE).status_code == 204
    assert not stored.exists()
    again = client.delete("/v1/documents", headers=hr, params=WHERE)
    assert again.status_code == 404 and again.json()["error"]["code"] == "document_not_found"
    sneaky = client.delete("/v1/documents", headers=hr, params=WHERE | {"filename": "..\\x.pdf"})
    assert sneaky.status_code == 422
