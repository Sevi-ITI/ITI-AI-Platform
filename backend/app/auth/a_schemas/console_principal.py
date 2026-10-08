from pydantic import BaseModel

from app.auth.a_schemas.console_role import ConsoleRole


class ConsolePrincipal(BaseModel):
    username: str
    role: ConsoleRole
    token_hash: str
