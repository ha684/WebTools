from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.tools.youtube.downloader import Downloader, DownloadError
from app.tools.youtube.jobs import JobManager
from app.tools.youtube.schemas import (
    Format,
    InfoRequest,
    Job,
    JobRequest,
    JobStatus,
    VideoInfo,
)

router = APIRouter(tags=["youtube"])

_MEDIA_TYPES = {Format.mp3: "audio/mpeg", Format.mp4: "video/mp4"}


def get_manager(request: Request) -> JobManager:
    manager: JobManager = request.app.state.youtube_jobs
    return manager


def get_downloader(request: Request) -> Downloader:
    downloader: Downloader = request.app.state.youtube_downloader
    return downloader


ManagerDep = Annotated[JobManager, Depends(get_manager)]
DownloaderDep = Annotated[Downloader, Depends(get_downloader)]


@router.post("/info")
def video_info(body: InfoRequest, downloader: DownloaderDep) -> VideoInfo:
    try:
        return downloader.fetch_info(body.url)
    except DownloadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/jobs", status_code=202)
def create_job(body: JobRequest, manager: ManagerDep) -> Job:
    return manager.create(body.url, body.format)


@router.get("/jobs")
def list_jobs(manager: ManagerDep) -> list[Job]:
    return manager.list()


@router.get("/jobs/{job_id}")
def get_job(job_id: str, manager: ManagerDep) -> Job:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job")
    return job


@router.get("/jobs/{job_id}/file")
def get_job_file(job_id: str, manager: ManagerDep) -> FileResponse:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job")
    path = manager.file_path(job_id)
    if job.status is not JobStatus.done or path is None:
        raise HTTPException(status_code=409, detail=f"Job is {job.status.value}, not done")
    return FileResponse(path, filename=path.name, media_type=_MEDIA_TYPES[job.format])
