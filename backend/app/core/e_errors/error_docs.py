"""error_docs(): a route's `responses=` for /docs: the statuses it can return, each with its error codes and what
they mean, so the C# and frontend devs see exactly which errors to handle on that route.
    error_docs("invalid_api_key", "conversation_not_found") -> {401: {...}, 404: {...}}"""

from app.core.e_errors.error_response import ErrorResponse

MEANINGS = {
    "invalid_api_key": (401, "key missing, wrong, revoked or expired"),
    "scope_forbidden": (403, "this key may not use this route"),
    "collection_forbidden": (403, "this key may not read that collection"),
    "collection_not_found": (404, "no collection with that name"),
    "conversation_not_found": (404, "no such conversation for this user (or it is someone else's)"),
    "invalid_request": (422, "a field or header is missing or invalid (e.g. no ITI-User-Id, question over 4,000)"),
    "internal_error": (500, "a bug on the AI side: quote the request_id"),
    "llm_busy": (503, "queue full: retry once after a pause"),
    "llm_unavailable": (503, "the model is down: no retry"),
}


def error_docs(*codes: str) -> dict:
    responses: dict = {}
    for code in codes:
        status, meaning = MEANINGS[code]
        line = f"**{code}**: {meaning}"
        if status in responses:
            responses[status]["description"] += f"\n\n{line}"
        else:
            responses[status] = {"model": ErrorResponse, "description": line}
    return dict(sorted(responses.items()))
