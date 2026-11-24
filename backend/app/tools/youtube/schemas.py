from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AfterValidator, BaseModel

# yt-dlp can fetch from hundreds of sites and local files; restricting the API to YouTube keeps
# it from becoming an SSRF / file-read primitive.
_ALLOWED_DOMAINS = ("youtube.com", "youtu.be")


def validate_youtube_url(value: str) -> str:
    value = value.strip()
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    is_youtube = any(host == d or host.endswith(f".{d}") for d in _ALLOWED_DOMAINS)
    if parsed.scheme not in {"http", "https"} or not is_youtube:
        raise ValueError("Only YouTube URLs (youtube.com, youtu.be) are supported")
    return value


YouTubeUrl = Annotated[str, AfterValidator(validate_youtube_url)]


class Format(StrEnum):
    mp3 = "mp3"
    mp4 = "mp4"


class JobStatus(StrEnum):
    queued = "queued"
    downloading = "downloading"
    converting = "converting"
    done = "done"
    error = "error"


class InfoRequest(BaseModel):
    url: YouTubeUrl


class VideoInfo(BaseModel):
    title: str
    uploader: str | None = None
    duration: int | None = None  # seconds
    thumbnail: str | None = None


class JobRequest(BaseModel):
    url: YouTubeUrl
    format: Format = Format.mp3


class Job(BaseModel):
    id: str
    url: str
    format: Format
    status: JobStatus = JobStatus.queued
    progress: float = 0.0  # 0-100
    title: str | None = None
    filename: str | None = None
    error: str | None = None
