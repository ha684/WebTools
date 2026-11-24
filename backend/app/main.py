from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """App factory."""
    settings = settings or get_settings()
    app = FastAPI(title="WebTools")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # New tool = new package under app/tools/ + one include_router line here.

    # In production the built frontend is served by the API itself (after the /api routes).
    if settings.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
    return app


app = create_app()
