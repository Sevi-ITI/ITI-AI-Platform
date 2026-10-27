"""app/ROUTES.md must match the routes the app really has (like test_contract_file.py for the C# contract).
If this fails after a route change, run from backend\\:  python -m scripts.export_routes"""

from scripts.export_routes import OUT, routes_markdown


def test_routes_file_is_up_to_date():
    assert OUT.read_text(encoding="utf-8") == routes_markdown(), "ROUTES.md is out of date: run python -m scripts.export_routes"


def test_every_route_says_who_may_call_it():
    rows = [line for line in routes_markdown().splitlines() if line.startswith("| ") and "`/" in line]
    assert len(rows) == 76  # 42 + 16 Tools & MCP routes (8.6d) + 2 Try it + 1 company apps + 2 app tools + 1 console collections + 2 chat docs + 1 suggestions + 4 security gate and code view (8.6e-3) + 4 company databases (8.6M) + 1 delete account (UI-R2g)
    anyone = sorted(row.split(" | ")[1] for row in rows if " | anyone | " in row)
    # the only routes without a login: health, the console login, and the chat API docs (they describe, every call needs a key)
    assert anyone == ["`/health`", "`/v1/console/login`", "`/v1/docs`", "`/v1/openapi.json`"]
