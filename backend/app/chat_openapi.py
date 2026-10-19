"""chat_openapi(): the API description the C# chat teams read at /v1/docs: the v1 contract (contract_openapi) cut down
to the chat routes (questions answered from the uploaded policies, RAG) and the ITI-Api-Key login. Uploads, admin,
console and tools routes are left out, and so is every schema only they use. The contract file itself
(integration-kit/openapi-v1.json) is unchanged: this is a view of it."""

import json

from app.contract_openapi import contract_openapi

CHAT_PATHS = (
    "/health",
    "/v1/chat",
    "/v1/chat/stream",
    "/v1/conversations",
    "/v1/conversations/{conversation_id}/messages",
)
DESCRIPTION = (
    "Ask questions answered only from ITI's uploaded documents, with file and page citations; "
    '"found": false is the "I don\'t know" reply, not an error.\n\n'
    "**Every call** sends `ITI-Api-Key` (press Authorize). Chat and history calls also send **`ITI-User-Id`**: "
    "the signed-in person's permanent id from your server's session. It is required, although this page marks it "
    "optional. Errors have one shape: `{\"error\": {\"code\", \"message\"}, \"request_id\"}`.\n\n"
    "The .NET client library, example and smoke test are in the integration kit (README.md)."
)


def chat_openapi() -> dict:
    spec = contract_openapi()
    spec["info"] = {"title": "ITI AI API: chat", "version": spec["info"]["version"], "description": DESCRIPTION}
    spec["paths"] = {path: spec["paths"][path] for path in CHAT_PATHS}
    for operation in (op for methods in spec["paths"].values() for op in methods.values()):
        if "security" in operation:  # the console's session login is not for apps
            operation["security"] = [s for s in operation["security"] if "ConsoleSession" not in s]

    components = spec["components"]
    components["securitySchemes"] = {"APIKeyHeader": components["securitySchemes"]["APIKeyHeader"]}
    used: set[str] = set()
    pending = [json.dumps(spec["paths"])]  # keep only the schemas the chat routes reach, directly or through others
    while pending:
        text = pending.pop()
        for name, schema in components["schemas"].items():
            if name not in used and f'"#/components/schemas/{name}"' in text:
                used.add(name)
                pending.append(json.dumps(schema))
    components["schemas"] = {name: schema for name, schema in components["schemas"].items() if name in used}
    return spec
