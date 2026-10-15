"""create_app(): builds the app: error handlers, middleware, then every feature's URL table.

Run on the laptop (from backend\\):  uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI

from app.admin.f_routes.router import router as admin_router
from app.chat.f_routes.router import router as chat_router
from app.console.f_routes.router import router as console_router
from app.core.e_errors.register_error_handlers import register_error_handlers
from app.core.i_middleware.request_id_and_timing import request_id_and_timing
from app.documents.f_routes.router import router as documents_router
from app.lifespan import lifespan
from app.ops.f_routes.router import router as ops_router
from app.tools.admin_api import router as tools_router

# Every feature's URL table. A new feature's router goes here; ROUTES.md lists every route (scripts/export_routes.py).
ROUTERS = (ops_router, chat_router, documents_router, admin_router, console_router, tools_router)


def create_app() -> FastAPI:
    app = FastAPI(title="ITI AI API", version="1.0.0", lifespan=lifespan,
                  swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"})
    register_error_handlers(app)
    app.middleware("http")(request_id_and_timing)
    for router in ROUTERS:
        app.include_router(router)
    return app

app = create_app()
