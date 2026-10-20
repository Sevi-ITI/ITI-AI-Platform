"""GET /health: "is the process up?" No database or model call, so it is cheap to poll."""


def get_health() -> dict[str, str]:
    """Is the service up? Replies {"status": "ok"}. No key needed; checks neither the database nor the model."""
    return {"status": "ok"}
