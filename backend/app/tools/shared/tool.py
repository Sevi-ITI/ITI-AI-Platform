"""Tool: one tool of the catalog (app/tools/catalog/*.py defines one TOOL each).
- spec: what the model sees (name, description, argument schema, the key scope it needs)
- args: the pydantic model that checks the model's arguments (extra fields refused: no employee_id)
- run(conn, employee_id, args) -> dict: the answer, from fixed queries only
- describe(result) -> (source title, holds data): "Records: payslip 2026-09-30", never values
- topic: a few words for the system prompt ("leave credits"); source: the system that answers ("records")"""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from app.tools.shared.tool_spec import ToolSpec


@dataclass(frozen=True)
class Tool:
    spec: ToolSpec
    args: type[BaseModel]
    run: Callable[..., dict]
    describe: Callable[[dict], tuple[str, bool]]
    topic: str
    source: str = "records"
