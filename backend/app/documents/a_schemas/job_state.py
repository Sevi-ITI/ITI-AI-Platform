"""JobState: the four states an ingestion job moves through."""

from typing import Literal

JobState = Literal["queued", "running", "done", "failed"]
