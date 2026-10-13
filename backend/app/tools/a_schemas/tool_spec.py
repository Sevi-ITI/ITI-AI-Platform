"""ToolSpec: what the model is told about one tool: its name, what it does and the arguments it may fill in.
The asking employee is never one of the arguments: run_tool adds it from ITI-User-Id."""

from pydantic import BaseModel


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict  # JSON schema of the arguments, in Ollama's "tools" format
    scope: str  # the key scope needed to be offered this tool, e.g. "records:read"

    def as_ollama(self) -> dict:
        function = {"name": self.name, "description": self.description, "parameters": self.parameters}
        return {"type": "function", "function": function}
