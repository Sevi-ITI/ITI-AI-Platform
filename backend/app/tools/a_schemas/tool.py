"""Tool: one entry of the tool registry: what the model sees (spec), how its arguments are checked
(args) and the function that answers it (run: connection, employee id, checked arguments -> result)."""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from app.tools.a_schemas.tool_spec import ToolSpec


@dataclass(frozen=True)
class Tool:
    spec: ToolSpec
    args: type[BaseModel]
    run: Callable[..., dict]

