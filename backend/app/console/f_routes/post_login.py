"""POST /v1/console/login: username + password -> a session pass (8 h).

ITI-Client-IP is the person's computer, set by Caddy (deploy/Caddyfile, header_up), which overwrites any value a
browser sends; the console passes it on. It is trusted only here: this route is reachable only through the console
(port 8000 is on 127.0.0.1, and Caddy's API site answers 404 for /v1/console/*). No header = "local" (the laptop
itself); a value that is not an IP address shares one "invalid" bucket. Used only by the login throttle (S2.1)."""

from ipaddress import ip_address

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.console.a_schemas.login_request import LoginRequest
from app.console.a_schemas.login_result import LoginResult
from app.console.d_service.log_in import log_in
from app.core.c_database.get_db import get_db


def post_login(
    body: LoginRequest,
    client_ip: str | None = Header(default=None, alias="ITI-Client-IP", max_length=64,
                                   description="The person's computer, set by Caddy. Leave it out on the laptop itself."),
    db: Session = Depends(get_db),
) -> LoginResult:
    if client_ip is None:
        computer = "local"
    else:
        try:
            computer = str(ip_address(client_ip.strip()))
        except ValueError:
            computer = "invalid"
    return log_in(db, body, computer)
