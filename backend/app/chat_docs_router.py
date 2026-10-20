"""chat_docs_router(): the C# chat teams' API docs. GET /v1/openapi.json (chat_openapi) and GET /v1/docs (Swagger UI
on that spec: Authorize with ITI-Api-Key, then Try it out). Anyone may open them, like /health: they describe routes,
every call on the page still needs a key. Left out of the API's own /docs (include_in_schema=False). Caddy lets
/v1/docs through on the API site (8443) and keeps the full /docs and /openapi.json hidden there."""

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.chat_openapi import chat_openapi

# Authorize moves up beside the title, so Swagger's empty bar under the description goes away (Vince, 2026-10-20).
# Phones keep Swagger's own layout: the button would squeeze the title.
PAGE_CSS = """<style>
.swagger-ui { position: relative; }
.swagger-ui .scheme-container { position: absolute; top: 50px; left: 0; right: 0; margin: 0; padding: 0;
  background: none; box-shadow: none; pointer-events: none; }
.swagger-ui .scheme-container .auth-wrapper { pointer-events: auto; }
.swagger-ui .information-container .info { padding-right: 170px; }
@media (max-width: 700px) {
  .swagger-ui .scheme-container { position: static; padding: 0 0 20px; }
  .swagger-ui .information-container .info { padding-right: 0; }
}
</style>"""


def chat_docs_router() -> APIRouter:
    router = APIRouter()
    spec = chat_openapi()  # built once at startup: it changes only with the code

    def get_chat_openapi() -> dict:
        return spec

    def get_chat_docs() -> HTMLResponse:
        # Swagger UI's scripts come from FastAPI's default public CDN (Vince, 2026-10-19): the devs' PCs have internet
        page = get_swagger_ui_html(openapi_url="/v1/openapi.json", title="ITI AI API: chat",
                                   swagger_ui_parameters={"persistAuthorization": False})
        return HTMLResponse(page.body.decode().replace("</head>", PAGE_CSS + "</head>", 1))

    router.add_api_route("/v1/openapi.json", get_chat_openapi, methods=["GET"], include_in_schema=False)
    router.add_api_route("/v1/docs", get_chat_docs, methods=["GET"], include_in_schema=False)
    return router
