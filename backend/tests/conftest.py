"""Shared fixtures: a fake Downloader (no network, no ffmpeg) wired into the real app."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.tools.youtube.downloader import DownloadError, Progress, ProgressCallback
from app.tools.youtube.schemas import Format, VideoInfo

VALID_URL = "https://www.youtube.com/watch?v=abc123"


class FakeDownloader:
    """Blocks inside download() until `gate` is set, so tests can observe in-flight jobs."""

    def __init__(self) -> None:
        self.gate = threading.Event()
        self.info_error: str | None = None
        self.download_error: str | None = None
        self.progress_before_gate: float | None = None
        self.urls_downloaded: list[str] = []

    def fetch_info(self, url: str) -> VideoInfo:
        if self.info_error:
            raise DownloadError(self.info_error)
        return VideoInfo(
            title="Fake Title",
            uploader="Fake Channel",
            duration=215,
            thumbnail="https://i.ytimg.com/x.jpg",
        )

    def download(self, url: str, fmt: Format, out_dir: Path, on_progress: ProgressCallback) -> Path:
        self.urls_downloaded.append(url)
        if self.progress_before_gate is not None:
            on_progress(Progress("downloading", self.progress_before_gate, "Fake Title"))
        assert self.gate.wait(timeout=5), "test never released the download gate"
        if self.download_error:
            raise DownloadError(self.download_error)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"Fake Title.{fmt.value}"
        path.write_bytes(b"fake-media-bytes")
        return path


@pytest.fixture
def fake() -> FakeDownloader:
    return FakeDownloader()


@pytest.fixture
def client(fake: FakeDownloader, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(downloader=fake, settings=Settings(download_dir=tmp_path))
    with TestClient(app) as c:
        yield c
    fake.gate.set()  # never leave a worker thread blocked


def wait_until(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition not reached within timeout")
