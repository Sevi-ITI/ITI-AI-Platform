"""GET /health: "is the process up?" No database or model call, so it is cheap to poll. It also says how to call
the chat routes (Vince, 2026-10-22: the .NET developers' first call): header names and FORMATS only, never a real
key, user or collection name, since anyone may call /health."""

HOW_TO_CALL = {
    "headers": {
        "ITI-Api-Key": "iti_sk_<12 hex>_<secret> (from Vince, server-side only)",
        "ITI-User-Id": "the signed-in person's permanent id, e.g. 10",
    },
    "collection": "lowercase letters, digits, dashes, e.g. iti-docs",
    "docs": "/v1/docs",
}


def get_health() -> dict[str, object]:
    """Is the service up? Replies {"status": "ok", "how_to_call": {...}}. No key needed; checks neither the database
    nor the model. `how_to_call` lists the headers and the collection format the chat routes expect (formats only)."""
    return {"status": "ok", "how_to_call": HOW_TO_CALL}
