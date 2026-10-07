"""SlotInfo: how many answers are being generated now, how many wait, and the limit."""

from pydantic import BaseModel


class SlotInfo(BaseModel):
    limit: int
    running: int
    waiting: int
