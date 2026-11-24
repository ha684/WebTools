"""Executable form of openspec/changes/add-youtube-downloader/specs/youtube-download/spec.md."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import VALID_URL, FakeDownloader, wait_until


def _job(client: TestClient, job_id: str) -> dict[str, object]:
    response = client.get(f"/api/youtube/jobs/{job_id}")
    assert response.status_code == 200, response.text
    return dict(response.json())


def _start(client: TestClient, fmt: str = "mp3", url: str = VALID_URL) -> dict[str, object]:
    response = client.post("/api/youtube/jobs", json={"url": url, "format": fmt})
    assert response.status_code == 202, response.text
    return dict(response.json())


def test_health_smoke(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


# --- Requirement: Inspect a video URL ---------------------------------------------------------


def test_info_returns_video_metadata(client: TestClient) -> None:
    """Scenario: Valid YouTube URL."""
    response = client.post("/api/youtube/info", json={"url": VALID_URL})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Fake Title"
    assert body["duration"] == 215
    assert {"uploader", "thumbnail"} <= body.keys()


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/video",
        "file:///etc/passwd",
        "https://youtube.com.evil.example/watch?v=1",  # suffix trick
        "https://notyoutube.com/watch?v=1",
        "not a url",
    ],
)
def test_info_rejects_non_youtube_urls(client: TestClient, url: str) -> None:
    """Scenario: Non-YouTube URL. The allowlist lives in schemas.validate_youtube_url."""
    response = client.post("/api/youtube/info", json={"url": url})
    assert response.status_code == 422, f"{url!r} was accepted: {response.text}"
    assert "YouTube" in response.text


@pytest.mark.parametrize(
    "url",
    [
        "https://youtu.be/abc123",
        "https://music.youtube.com/watch?v=abc123",
        "https://m.youtube.com/watch?v=abc123",
    ],
)
def test_info_accepts_youtube_host_variants(client: TestClient, url: str) -> None:
    assert client.post("/api/youtube/info", json={"url": url}).status_code == 200


def test_info_returns_502_with_extractor_message(client: TestClient, fake: FakeDownloader) -> None:
    """Scenario: Video cannot be resolved."""
    fake.info_error = "Video unavailable. This video is private"
    response = client.post("/api/youtube/info", json={"url": VALID_URL})
    assert response.status_code == 502
    assert "This video is private" in response.text


# --- Requirement: Start a download job --------------------------------------------------------


def test_job_is_accepted_immediately_then_completes(
    client: TestClient, fake: FakeDownloader
) -> None:
    """Scenario: Job accepted."""
    job = _start(client)
    assert job["id"]
    assert job["status"] in {"queued", "downloading"}
    fake.gate.set()
    wait_until(lambda: _job(client, str(job["id"]))["status"] == "done")


def test_unsupported_format_is_rejected(client: TestClient) -> None:
    """Scenario: Unsupported format."""
    response = client.post("/api/youtube/jobs", json={"url": VALID_URL, "format": "flac"})
    assert response.status_code == 422
    assert "mp3" in response.text and "mp4" in response.text


def test_playlist_url_is_passed_through_for_single_video_handling(
    client: TestClient, fake: FakeDownloader
) -> None:
    """Scenario: Playlist parameters are ignored — the URL is accepted as-is; the downloader
    adapter enforces noplaylist (see test_ytdlp_options)."""
    url = f"{VALID_URL}&list=RDabc123&start_radio=1&t=4825s"
    _start(client, url=url)
    fake.gate.set()
    wait_until(lambda: fake.urls_downloaded == [url])


# --- Requirement: Track job progress ----------------------------------------------------------


def test_running_job_reports_progress_between_0_and_100(
    client: TestClient, fake: FakeDownloader
) -> None:
    """Scenario: Job in progress."""
    fake.progress_before_gate = 42.0
    job = _start(client)
    wait_until(lambda: _job(client, str(job["id"]))["progress"] == 42.0)
    current = _job(client, str(job["id"]))
    assert current["status"] == "downloading", current
    assert client.get("/api/youtube/jobs").json()[0]["id"] == job["id"]


def test_unknown_job_is_404(client: TestClient) -> None:
    """Scenario: Unknown job."""
    assert client.get("/api/youtube/jobs/nope").status_code == 404
    assert client.get("/api/youtube/jobs/nope/file").status_code == 404


def test_failed_download_marks_job_error_and_api_keeps_serving(
    client: TestClient, fake: FakeDownloader
) -> None:
    """Scenario: Download fails."""
    fake.download_error = "ffmpeg not found"
    job = _start(client)
    fake.gate.set()
    wait_until(lambda: _job(client, str(job["id"]))["status"] == "error")
    assert "ffmpeg not found" in str(_job(client, str(job["id"]))["error"])
    assert client.get("/api/health").status_code == 200


# --- Requirement: Retrieve the finished file --------------------------------------------------


def test_finished_file_is_served_as_attachment(client: TestClient, fake: FakeDownloader) -> None:
    """Scenario: File ready."""
    job = _start(client, fmt="mp4")
    fake.gate.set()
    wait_until(lambda: _job(client, str(job["id"]))["status"] == "done")
    response = client.get(f"/api/youtube/jobs/{job['id']}/file")
    assert response.status_code == 200, response.text
    assert response.content == b"fake-media-bytes"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment") and ".mp4" in disposition


def test_file_of_unfinished_job_is_409(client: TestClient) -> None:
    """Scenario: File not ready."""
    job = _start(client)
    assert client.get(f"/api/youtube/jobs/{job['id']}/file").status_code == 409
