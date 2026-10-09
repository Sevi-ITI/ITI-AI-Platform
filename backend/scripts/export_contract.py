"""export_contract: writes the v1 contract for the C# apps to integration-kit/openapi-v1.json.
Run it after a deliberate change to a chat, conversation or document route, then commit the file.

Run from backend\\:
    python -m scripts.export_contract
"""

import json
from pathlib import Path

from app.contract_openapi import contract_openapi

CONTRACT = Path(__file__).resolve().parents[2] / "integration-kit" / "openapi-v1.json"


def main() -> None:
    CONTRACT.write_text(json.dumps(contract_openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {CONTRACT}")

if __name__ == "__main__":
    main()
