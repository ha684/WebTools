from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.tools import youtube
from app.tools.youtube.downloader import Downloader, YtDlpDownloader
from app.tools.youtube.jobs import JobManager


def create_app(downloader: Downloader | None = None, settings: Settings | None = None) -> FastAPI:
    """App factory. Tests pass a fake `downloader` and a temp `settings.download_dir`."""
    settings = settings or get_settings()
    downloader = downloader or YtDlpDownloader(settings)
    jobs = JobManager(downloader, settings.download_dir, settings.max_workers)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        jobs.shutdown()

    app = FastAPI(title="WebTools", lifespan=lifespan)
    app.state.youtube_downloader = downloader
    app.state.youtube_jobs = jobs

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # New tool = new package under app/tools/ + one include_router line here.
    app.include_router(youtube.router, prefix="/api/youtube")

    # In production the built frontend is served by the API itself (after the /api routes).
    if settings.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
    return app


app = create_app()
