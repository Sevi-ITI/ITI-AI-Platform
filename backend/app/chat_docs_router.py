"""chat_docs_router(): the C# chat teams' API docs. GET /v1/openapi.json (chat_openapi) and GET /v1/docs (Swagger UI
on that spec: Authorize with ITI-Api-Key, then Try it out). Anyone may open them, like /health: they describe routes,
every call on the page still needs a key. Left out of the API's own /docs (include_in_schema=False). Caddy lets
/v1/docs through on the API site (8443) and keeps the full /docs and /openapi.json hidden there."""

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.chat_openapi import chat_openapi


def chat_docs_router() -> APIRouter:
    router = APIRouter()
    spec = chat_openapi()  # built once at startup: it changes only with the code

    def get_chat_openapi() -> dict:
        return spec

    def get_chat_docs() -> HTMLResponse:
        # Swagger UI's scripts come from FastAPI's default public CDN (Vince, 2026-10-19): the devs' PCs have internet
        return get_swagger_ui_html(openapi_url="/v1/openapi.json", title="ITI AI API: chat",
                                   swagger_ui_parameters={"persistAuthorization": False})

    router.add_api_route("/v1/openapi.json", get_chat_openapi, methods=["GET"], include_in_schema=False)
    router.add_api_route("/v1/docs", get_chat_docs, methods=["GET"], include_in_schema=False)
    return router
