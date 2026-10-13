"""McpServerConfig: one entry of ITI_MCP_SERVERS: an MCP server whose tools the chat model may use.
Plain http is allowed only on this computer (127.0.0.1 / localhost); any other host must be https, so the
shared secret and employee ids never cross the network unencrypted (decision D3, Phase 8.5)."""

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class McpServerConfig(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,30}$")  # tool names become "<name>__<tool>"
    url: str  # e.g. http://127.0.0.1:8100/mcp
    scope: str  # the key scope needed to be offered this server's tools, e.g. "records:read"
    token: str = Field(min_length=16, repr=False)  # shared secret, sent as "Authorization: Bearer <token>"

    @field_validator("url")
    @classmethod
    def https_unless_local(cls, url: str) -> str:
        parts = urlparse(url)
        if parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in LOCAL_HOSTS):
            return url
        raise ValueError("must be https (plain http only for 127.0.0.1 / localhost)")
