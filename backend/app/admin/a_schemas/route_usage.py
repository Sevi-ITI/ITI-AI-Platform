"""RouteUsage: requests, errors and p95 time for one endpoint in the chosen window."""

from pydantic import BaseModel


class RouteUsage(BaseModel):
    route: str
    requests: int
    errors: int
    p95_ms: int | None
