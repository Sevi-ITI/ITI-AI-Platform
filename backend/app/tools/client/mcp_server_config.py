"""McpServerConfig: one checked entry of MCP_SERVERS (client/servers.py).
Plain http is allowed only on this computer (127.0.0.1 / localhost); any other host must be https, so the
shared secret and employee ids never cross the network unencrypted (decision D3, Phase 8.5)."""

from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class McpServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a typo in servers.py is an error, not a silently ignored field

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,30}$")  # tool names become "<name>__<tool>"
    url: str  # e.g. http://127.0.0.1:8100/mcp
    scope: str  # the key scope needed to be offered this server's tools, e.g. "records:read"
    token_env: str = Field(pattern=r"^ITI_MCP_[A-Z0-9_]+$")  # the env variable holding the shared secret
    topics: list[str] = Field(min_length=1)  # for the system prompt, e.g. ["leave credits"]
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def https_unless_local(cls, url: str) -> str:
        parts = urlparse(url)
        if parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in LOCAL_HOSTS):
            return url
        raise ValueError("must be https (plain http only for 127.0.0.1 / localhost)")
