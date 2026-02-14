from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from vulture.api.routes import router as api_router
from vulture.config import get_settings
from vulture.db.init import init_database
from vulture.web.routes import router as web_router


def create_app() -> FastAPI:
    settings = get_settings()
    project_root = Path(__file__).resolve().parents[3]
    static_dir = project_root / "src" / "vulture" / "web" / "static"

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_database()

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app.include_router(api_router)
    if settings.web_ui_enabled:
        app.include_router(web_router)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return app
