# WebTools

A small personal toolbox for web chores, with a browser UI over a FastAPI backend. Each helper is a self-contained "tool"; new ones plug in without touching the others.

**Tools**

- **YouTube downloader** — paste a link, pick mp3 (audio) or mp4 (video), watch progress, save the file. Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and ffmpeg.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.11+ is fetched automatically)
- Node.js 20+ (also used by yt-dlp as its JavaScript runtime for YouTube)
- [ffmpeg](https://ffmpeg.org/) on `PATH`
- GNU make (optional but the commands below use it)

## Quick start

```sh
make setup   # install backend + frontend deps
make dev     # API on :8000, UI on :5173  ->  open http://localhost:5173
```

Downloads are written to `downloads/<job-id>/` and also offered through the browser.

Single-process mode (what you would deploy): `npm --prefix frontend run build`, then `cd backend && uv run uvicorn app.main:app` — FastAPI serves the built UI and the API on one port.

## Configuration

Environment variables, all optional:

| Variable | Default | Purpose |
|---|---|---|
| `WEBTOOLS_DOWNLOAD_DIR` | `<repo>/downloads` | where files are written |
| `WEBTOOLS_JS_RUNTIME` | `node` | JS runtime for yt-dlp (`node`, `deno`, `bun`, ...) |
| `WEBTOOLS_FFMPEG_LOCATION` | _(PATH)_ | folder or binary of ffmpeg |
| `WEBTOOLS_MAX_WORKERS` | `2` | concurrent downloads |

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/youtube/info` | metadata for a URL (`{url}`) |
| POST | `/api/youtube/jobs` | start a download (`{url, format: "mp3"\|"mp4"}`) → 202 + job |
| GET | `/api/youtube/jobs` / `/{id}` | list jobs / one job (`status`, `progress`, `error`) |
| GET | `/api/youtube/jobs/{id}/file` | the finished file as an attachment |

Interactive docs at `http://localhost:8000/docs`. Only YouTube URLs are accepted; playlist parameters in a URL are ignored (single video only).

## Development

```sh
make test T=backend/tests/test_youtube_api.py   # a subset
make lint                                       # ruff, mypy --strict, oxlint, tsc
make check                                      # everything
```

Adding a tool: create `backend/app/tools/<name>/` (router, schemas, service), add one `include_router` line in `backend/app/main.py`, then a folder under `frontend/src/tools/<name>/` registered in `frontend/src/App.tsx`.

YouTube changes often; if downloads start failing, update yt-dlp: `cd backend && uv lock --upgrade-package yt-dlp && uv sync`.

## Notes

For personal use. Only download content you have the right to download; respect YouTube's Terms of Service and copyright law.
