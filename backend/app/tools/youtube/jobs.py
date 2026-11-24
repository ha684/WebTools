"""In-memory job tracking on a small thread pool. Jobs are lost on restart (files stay on disk)."""

from __future__ import annotations

import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.tools.youtube.downloader import Downloader, Progress
from app.tools.youtube.schemas import Format, Job, JobStatus

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class JobManager:
    def __init__(self, downloader: Downloader, download_dir: Path, max_workers: int = 2) -> None:
        self._downloader = downloader
        self._download_dir = download_dir
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="yt-dl")
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._files: dict[str, Path] = {}

    def create(self, url: str, fmt: Format) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], url=url, format=fmt)
        with self._lock:
            self._jobs[job.id] = job
        self._pool.submit(self._run, job.id)
        return self.get(job.id) or job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy() if job else None

    def list(self) -> list[Job]:
        with self._lock:
            return [j.model_copy() for j in reversed(self._jobs.values())]  # newest first

    def file_path(self, job_id: str) -> Path | None:
        with self._lock:
            return self._files.get(job_id)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _update(self, job_id: str, **fields: object) -> None:
        with self._lock:
            self._jobs[job_id] = self._jobs[job_id].model_copy(update=fields)

    def _on_progress(self, job_id: str, event: Progress) -> None:
        with self._lock:
            job = self._jobs[job_id]
            # mp4 downloads video then audio; never move the bar backwards, never claim 100 early
            progress = max(job.progress, min(event.percent, 99.0))
            self._jobs[job_id] = job.model_copy(
                update={
                    "status": JobStatus(event.stage),
                    "progress": progress,
                    "title": event.title or job.title,
                }
            )

    def _run(self, job_id: str) -> None:
        job = self._jobs[job_id]
        self._update(job_id, status=JobStatus.downloading)
        try:
            path = self._downloader.download(
                job.url,
                job.format,
                self._download_dir / job_id,
                lambda event: self._on_progress(job_id, event),
            )
        except Exception as exc:  # noqa: BLE001 - any failure becomes a visible job error
            self._update(job_id, status=JobStatus.error, error=_ANSI.sub("", str(exc)).strip())
            return
        with self._lock:
            self._files[job_id] = path
        self._update(job_id, status=JobStatus.done, progress=100.0, filename=path.name)
