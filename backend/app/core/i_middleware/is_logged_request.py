"""is_logged_request(): which requests get a request_logs row. Everything except reads of /health,
/v1/admin/* and /v1/console/*: the console polls those every few seconds and would bury the real traffic.
Console logins and logouts are POSTs, so they are logged."""

def is_logged_request(method: str, path: str) -> bool:
    if method == "GET" and (path == "/health" or path.startswith(("/v1/admin/", "/v1/console/"))):
        return False
    return True
