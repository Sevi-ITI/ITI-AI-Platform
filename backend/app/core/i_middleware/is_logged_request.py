"""is_logged_request(): which requests get a request_logs row. Everything except reads of /health
and of /v1/admin/*: your admin page polls those every few seconds and would bury the real traffic."""

def is_logged_request(method: str, path: str) -> bool:
    if method == "GET" and (path == "/health" or path.startswith("/v1/admin/")):
        return False
    return True