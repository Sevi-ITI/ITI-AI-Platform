"""PasswordReset: the body of POST /v1/admin/accounts/{username}/password. Never echoed in errors."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class PasswordReset(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    password: SecretStr = Field(min_length=12, max_length=128)
