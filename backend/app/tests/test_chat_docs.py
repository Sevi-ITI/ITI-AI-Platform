"""The C# chat teams' API docs (/v1/docs, /v1/openapi.json): only the chat routes and the key login, out of the API's
own /docs, and not written to the request log."""

from app.chat_openapi import CHAT_PATHS


def test_the_chat_spec_holds_only_the_chat_routes_and_the_key_login(client):
    spec = client.get("/v1/openapi.json").json()
    assert list(spec["paths"]) == list(CHAT_PATHS)
    assert list(spec["components"]["securitySchemes"]) == ["APIKeyHeader"]
    text = str(spec)
    for hidden in ("/v1/documents", "/v1/admin", "/v1/console", "ConsoleSession", "UploadAccepted", "JobStatus"):
        assert hidden not in text, hidden
    assert spec["info"]["title"] == "ITI AI API: chat" and "ITI-User-Id" in spec["info"]["description"]


def test_the_docs_page_uses_that_spec_and_stays_out_of_the_full_docs_and_the_log(client, make_key):
    page = client.get("/v1/docs")
    assert page.status_code == 200 and "/v1/openapi.json" in page.text and "swagger" in page.text.lower()
    assert not {"/v1/docs", "/v1/openapi.json"} & set(client.get("/openapi.json").json()["paths"])

    admin = make_key("iti-admin", ["admin"], [])
    logged = {row["path"] for row in client.get("/v1/admin/requests", headers=admin).json()}
    assert not {"/v1/docs", "/v1/openapi.json"} & logged
