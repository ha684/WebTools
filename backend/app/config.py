from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Env vars use the WEBTOOLS_ prefix, e.g. WEBTOOLS_JS_RUNTIME=deno."""

    model_config = SettingsConfigDict(env_prefix="WEBTOOLS_")

    download_dir: Path = REPO_ROOT / "downloads"
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"
    js_runtime: str = "node"  # yt-dlp needs a JS runtime for YouTube; Node is the common one
    ffmpeg_location: str | None = None  # None = find ffmpeg on PATH
    max_workers: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
