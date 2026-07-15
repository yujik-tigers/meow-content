# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Daily cat mailing content server: scrapes reddit cat memes and quotes, runs them through an LLM analysis/approval pipeline, and serves one approved content per day. FastAPI backend (`app/`) + Streamlit admin UI (`view/meme_inspection.py`), MySQL + Qdrant, deployed to EC2 via Docker.

## Commands

```bash
poetry install                      # deps (Python 3.13, Poetry)
poetry run playwright install chromium   # browser for the reddit scraper

docker compose up -d mysql qdrant   # local infra (app service is commented out)
poetry run uvicorn app.main:app --reload            # API server (needs .env)
poetry run streamlit run view/meme_inspection.py    # admin UI

poetry run pytest                   # all tests (coverage on app/)
poetry run pytest tests/scrap/test_reddit_meme_scraper.py::test_scrape_via_json_success  # single test
poetry run ruff check .             # lint
poetry run pyright                  # type check (standard mode)
```

A populated `.env` at the repo root is required to import `app.settings` (all fields are required, no defaults). Tests don't need `.env`: `tests/conftest.py` sets fake env vars via `os.environ.setdefault` **before** app imports — when adding a required setting, add it to both `.env` and `conftest.py`, and update the `ENV_FILE_CONTENT` GitHub secret before deploying.

## Architecture

### Content lifecycle (the core domain)

Everything revolves around one MySQL table `content` (`ContentRecord` in `app/repository/mysql/_models.py`) shared by all content types (`ContentType`: reddit_meme, quote, literal_quote, fact) and moved through `ContentStatus`: `RAW → ANALYZED/PENDING → APPROVED → USED` (or `REJECTED`).

1. **Ingest**: admin-triggered — `POST /api/v1/admin/scrap` (`app/router/admin.py`) takes a `ScrapingRequest{content_type}` body, resolves a `Scraper` via `ScraperFactory` (`app/scrap/`), and inserts rows with `status=RAW`, deduplicating by `image_url`/quote text in `create_contents`. There is no scheduled scraping job — trigger it manually (e.g. the Streamlit admin UI's "지금 스크래핑 실행" button, one request per content type).
2. **Curate**: admin API (`app/router/admin.py`, `/api/v1/admin`) + Streamlit UI analyze content with LLMs (`app/analyzer/`), generate images (`app/image_generator/`), and approve/reject.
3. **Serve**: `_daily_content_job` reserves one APPROVED content per day (odd day = quote, even day = meme) marking it USED; public API (`app/router/content.py`, `GET /api/v1/contents/?date=`) returns it.

### Repository layer boundary (enforced)

Ruff rule TID251 bans importing `app.repository.mysql._models` anywhere except `repository.py` and `tests/**`. All other code uses domain dataclasses from `app/schema/content.py`: `Content` (persisted, read model) and `NewContent` (pre-insert, create DTO). Conversions happen only inside `MySQLContentRepository` (`_to_record` / `_to_new_record`). Write methods use the `@transactional` decorator (commit/rollback around the method).

There are no migrations — `create_tables()` runs `SQLModel.metadata.create_all()` at startup, so schema changes mean editing the models (existing columns are not altered automatically).

### Scheduler

`AsyncIOScheduler` (Asia/Seoul) is created in the FastAPI lifespan, so scheduled jobs run inside the API process only — the Streamlit container overrides CMD and never runs them. It only registers `_daily_content_job` (daily content reservation); scraping has no cron job and is triggered on-demand via the admin API instead.

### Scraper package (`app/scrap/`)

Mirrors the `app/analyzer/`/`app/image_generator/` domain-package pattern: `base.py` defines the `Scraper` ABC (`async def scrape() -> list[NewContent]`), `reddit_meme_scraper.py`/`daily_quote_scraper.py` implement it (each exporting a module-level singleton), and `factory.py`'s `ScraperFactory.get_scraper(content_type)` dispatches between them. There is no separate HTTP/browser client layer — each scraper owns its own fetching logic directly.

### Reddit scraping quirk

`www.reddit.com/.../top.json` returns 403 even from a real browser. `RedditMemeScraper` (`app/scrap/reddit_meme_scraper.py`) launches headless Playwright Chromium (`--no-sandbox` etc. for Docker), tries the JSON endpoint first, and falls back to parsing `old.reddit.com` HTML (`div.thing[data-url]`) — the fallback is currently the path that actually works, so a WARNING log on every scrape trigger is expected.

### LLM usage tracking

An HTTP middleware in `app/main.py` sets a `ContextVar` LangChain callback handler (`app/usage/usage_tracking.py`) that records token usage per model to the `token_usage` table; `app/usage/pricing.py` + `GET /api/v1/admin/usage/cost` surface cost in the admin UI. Analyzers and image generators are chosen by factories keyed on `ContentType`/model enums.

### Deployment

Pushing to `main` triggers `.github/workflows/main.yml`: build/push the Docker image, then SSH to EC2 and restart two containers from the same image (`meow-content` = uvicorn, `meow-streamlit` = streamlit with CMD override). The Dockerfile installs Chromium headless-shell (`playwright install --with-deps --only-shell chromium`). Prod env comes from the `ENV_FILE_CONTENT` secret, not the repo `.env`.

## Testing conventions

`asyncio_mode = "auto"` — async tests need no decorator. Tests are mock-based (no DB/network): repositories are tested with `AsyncMock` sessions, routers via the `client` fixture in `tests/conftest.py` (httpx `ASGITransport` + `dependency_overrides`), and pure parsing logic is tested directly. Known pre-existing failures: 2 tests in `tests/image_generator/test_image_text_renderer.py` fail locally due to font environment.
