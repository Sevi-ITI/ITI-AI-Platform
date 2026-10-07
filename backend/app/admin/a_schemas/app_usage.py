"""AppUsage: requests and errors for one calling app in the chosen window."""

from pydantic import BaseModel


class AppUsage(BaseModel):
    app_id: str
    requests: int
    errors: int
