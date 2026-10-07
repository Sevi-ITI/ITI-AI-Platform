"""GET /health: "is the process up?" No database or model call, so it is cheap to poll."""


def get_health() -> dict[str, str]:
    return {"status": "ok"}
