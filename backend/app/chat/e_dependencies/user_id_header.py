"""UserIdHeader: the ITI-User-Id header type: the end user, as the calling app identifies them."""

from typing import Annotated

from fastapi import Header

UserIdHeader = Annotated[str, Header(alias="ITI-User-Id", min_length=1, max_length=100)]
