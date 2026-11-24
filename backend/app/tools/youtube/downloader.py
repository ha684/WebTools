"""Adapter between our job system and yt-dlp. Everything yt-dlp-specific lives in this file."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpError

from app.config import Settings
from app.tools.youtube.schemas import Format, VideoInfo

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class DownloadError(Exception):
    """A user-presentable failure (private video, ffmpeg missing, network...)."""


@dataclass(frozen=True)
class Progress:
    stage: Literal["downloading", "converting"]
    percent: float = 0.0
    title: str | None = None


ProgressCallback = Callable[[Progress], None]


class Downloader(Protocol):
    def fetch_info(self, url: str) -> VideoInfo: ...

    def download(
        self, url: str, fmt: Format, out_dir: Path, on_progress: ProgressCallback
    ) -> Path: ...


def _base_opts(settings: Settings) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "noplaylist": True,  # a watch URL with list=RD…&start_radio=1 must stay a single video
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "js_runtimes": {settings.js_runtime: {}},
    }
    if settings.ffmpeg_location:
        opts["ffmpeg_location"] = settings.ffmpeg_location
    return opts


def build_ydl_opts(settings: Settings, fmt: Format, out_dir: Path) -> dict[str, Any]:
    opts = _base_opts(settings)
    opts["outtmpl"] = str(out_dir / "%(title)s [%(id)s].%(ext)s")
    opts["windowsfilenames"] = True
    if fmt is Format.mp3:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}
        ]
    else:
        opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"
    return opts


def _clean(exc: Exception) -> str:
    return _ANSI.sub("", str(exc)).strip()


class YtDlpDownloader:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_info(self, url: str) -> VideoInfo:
        try:
            with YoutubeDL({**_base_opts(self._settings), "skip_download": True}) as ydl:
                info = ydl.extract_info(url, download=False)
        except YtDlpError as exc:
            raise DownloadError(_clean(exc)) from exc
        if not info:
            raise DownloadError("No video information returned")
        duration = info.get("duration")
        return VideoInfo(
            title=info.get("title") or "Untitled",
            uploader=info.get("uploader"),
            duration=int(duration) if duration is not None else None,
            thumbnail=info.get("thumbnail"),
        )

    def download(self, url: str, fmt: Format, out_dir: Path, on_progress: ProgressCallback) -> Path:
        def on_download(d: dict[str, Any]) -> None:
            if d.get("status") != "downloading":
                return
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            percent = d.get("downloaded_bytes", 0) / total * 100 if total else 0.0
            title = (d.get("info_dict") or {}).get("title")
            on_progress(Progress("downloading", percent, title))

        def on_postprocess(d: dict[str, Any]) -> None:
            if d.get("status") == "started":
                on_progress(Progress("converting", 100.0, (d.get("info_dict") or {}).get("title")))

        opts = build_ydl_opts(self._settings, fmt, out_dir)
        opts["progress_hooks"] = [on_download]
        opts["postprocessor_hooks"] = [on_postprocess]
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except YtDlpError as exc:
            raise DownloadError(_clean(exc)) from exc

        for item in (info or {}).get("requested_downloads") or []:
            filepath = item.get("filepath")
            if filepath and Path(filepath).exists():
                return Path(filepath)
        produced = sorted(out_dir.glob(f"*.{fmt.value}"))
        if not produced:
            raise DownloadError("Download finished but no output file was found")
        return produced[-1]
