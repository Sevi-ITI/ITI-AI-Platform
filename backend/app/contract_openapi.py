"""contract_openapi(): the v1 contract for ITI's C# apps: the OpenAPI spec of only the routes an app
calls (health, chat, conversations, documents). Admin and console routes stay out on purpose.
Saved as integration-kit/openapi-v1.json; test_contract_file.py fails when the two differ."""

from fastapi import FastAPI

from app.chat.f_routes.router import router as chat_router
from app.documents.f_routes.router import router as documents_router
from app.ops.f_routes.router import router as ops_router


def contract_openapi() -> dict:
    app = FastAPI(title="ITI AI API", version="1.0.0")
    for router in (ops_router, chat_router, documents_router):
        app.include_router(router)
    return app.openapi()
