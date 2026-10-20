"""contract_openapi(): the v1 contract for ITI's C# apps: the OpenAPI spec of only the routes an app
calls (health, chat, conversations, documents). Admin and console routes stay out on purpose.
Saved as integration-kit/openapi-v1.json; test_contract_file.py fails when the two differ.
Two fixes on what FastAPI generates, so the contract says what an app really gets:
- ITI-User-Id is required: app keys get 422 without it (it is optional in code only for console sessions).
- The stream's errors are JSON: they come before the stream starts (FastAPI labels them text/event-stream)."""

from fastapi import FastAPI

from app.chat.f_routes.router import router as chat_router
from app.documents.f_routes.router import router as documents_router
from app.ops.f_routes.router import router as ops_router


def contract_openapi() -> dict:
    app = FastAPI(title="ITI AI API", version="1.0.0")
    for router in (ops_router, chat_router, documents_router):
        app.include_router(router)
    spec = app.openapi()

    for operation in (op for methods in spec["paths"].values() for op in methods.values()):
        for param in operation.get("parameters", []):
            if param["name"] == "ITI-User-Id":
                param["required"] = True
                param["schema"] = {"type": "string", "maxLength": 100, "title": "Iti-User-Id"}
        for status, response in operation["responses"].items():
            if status != "200" and "text/event-stream" in response.get("content", {}):
                response["content"] = {"application/json": response["content"]["text/event-stream"]}
    return spec
