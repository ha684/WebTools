# Stable command names, so an agent never has to guess how this project runs.
# Monorepo: backend/ (uv, FastAPI) and frontend/ (npm, Vite). `check` runs both areas.

.PHONY: help setup dev dev-be dev-fe test test-be test-fe lint lint-be lint-fe check

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

setup: ## Install backend + frontend dependencies (needs uv, node, ffmpeg)
	cd backend && uv sync
	npm --prefix frontend install
	@command -v ffmpeg >/dev/null 2>&1 || echo "WARNING: ffmpeg not on PATH - mp3/mp4 conversion will fail"
	@command -v node >/dev/null 2>&1 || echo "WARNING: node not on PATH - yt-dlp needs a JS runtime for YouTube"

dev: ## Run API (:8000) and UI (:5173) together; open http://localhost:5173
	@$(MAKE) --no-print-directory -j2 dev-be dev-fe

dev-be:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-fe:
	npm --prefix frontend run dev

# T narrows the run: `make test T=backend/tests/test_youtube_api.py`, `make test T=frontend/src/api.test.ts`,
# or a pytest selector like `T="backend/tests -k playlist"`. Empty runs everything.
test: ## Run tests; narrow with T=<path or selector> (backend/... or frontend/... prefix picks the area)
ifeq ($(T),)
	@$(MAKE) --no-print-directory test-be test-fe
else ifneq ($(filter frontend/%,$(T)),)
	@$(MAKE) --no-print-directory test-fe T="$(T)"
else
	@$(MAKE) --no-print-directory test-be T="$(T)"
endif

test-be:
	cd backend && uv run pytest -q $(patsubst backend/%,%,$(T))

test-fe:
	npm --prefix frontend test -- $(patsubst frontend/%,%,$(T))

lint: lint-be lint-fe ## Fast static checks: format, lint, types (both areas)

lint-be:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy

lint-fe:
	npm --prefix frontend run lint
	npm --prefix frontend run typecheck

check: lint ## Full check - run once when a change is complete, not after every edit
	@$(MAKE) --no-print-directory test T=
