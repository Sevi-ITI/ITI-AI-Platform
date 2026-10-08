"""LoginRequest: the body of POST /v1/console/login. Like AccountCreate, a refused field is never echoed."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class LoginRequest(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    username: str = Field(min_length=1, max_length=32)  # any case: "Vince" logs in as "vince"
    password: SecretStr = Field(min_length=1, max_length=128)
