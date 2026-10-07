"""new_id(): a short random id in the ITI format, e.g. new_id("job") -> "iti_job_3f9a1c2b7e4d"."""

import uuid


def new_id(kind: str) -> str:
    return f"iti_{kind}_{uuid.uuid4().hex[:12]}"
