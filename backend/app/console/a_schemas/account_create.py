"""AccountCreate: a new console account (the create_console_user script now, the Accounts page later).
The password is a SecretStr, so it never shows in logs or repr(). hide_input_in_errors: a refused
field is not echoed in the error text either (Pydantic repeats the typed value by default)."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.auth.a_schemas.console_role import ConsoleRole


class AccountCreate(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    username: str = Field(pattern=r"^[a-z][a-z0-9._-]{2,31}$")  # lowercase, 3-32 characters, e.g. "vince", "j.santos"
    display_name: str | None = Field(default=None, max_length=100)
    role: ConsoleRole
    password: SecretStr = Field(min_length=12, max_length=128)
