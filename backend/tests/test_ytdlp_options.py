"""The yt-dlp adapter is the one place the real downloader's behavior is decided; test its options
without touching the network."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.tools.youtube.downloader import build_ydl_opts
from app.tools.youtube.schemas import Format


def test_never_downloads_whole_playlists(tmp_path: Path) -> None:
    """Spec: Playlist parameters are ignored (a list=RD…&start_radio=1 URL is a mix)."""
    for fmt in Format:
        assert build_ydl_opts(Settings(), fmt, tmp_path)["noplaylist"] is True


def test_mp3_extracts_best_quality_audio(tmp_path: Path) -> None:
    opts = build_ydl_opts(Settings(), Format.mp3, tmp_path)
    (pp,) = opts["postprocessors"]
    assert pp["key"] == "FFmpegExtractAudio"
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "0"


def test_mp4_merges_into_mp4(tmp_path: Path) -> None:
    assert build_ydl_opts(Settings(), Format.mp4, tmp_path)["merge_output_format"] == "mp4"


def test_js_runtime_comes_from_settings(tmp_path: Path) -> None:
    """yt-dlp needs a JS runtime for YouTube; without one formats go missing."""
    opts = build_ydl_opts(Settings(js_runtime="deno"), Format.mp3, tmp_path)
    assert opts["js_runtimes"] == {"deno": {}}
