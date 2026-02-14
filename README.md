# Vulture

## 1. Project Overview

Vulture is a local-first autonomous job application assistant that helps you parse job postings, tailor application documents, and execute structured application runs with configurable human approval gates.

The project combines:
- Browser automation for application workflows (`browser-use`).
- A local SQLite-backed profile and run-history store.
- Hybrid LLM routing across OpenAI and local OpenAI-compatible providers.
- A FastAPI backend with both JSON API endpoints and an HTMX web dashboard.
- A Typer CLI for initialization, profile management, run control, and operations.

Vulture is designed to keep artifacts and state local by default (`./data`), and to pause for user decisions when confidence or policy requires it.

## 2. Core Capabilities

- Job intake and parsing from a job posting URL.
- Structured job analysis (title, company, location, requirements, responsibilities).
- Tailored resume and cover letter generation per run.
- Profile patch suggestion pipeline to improve stored candidate data.
- Configurable run modes (`strict`, `medium`, `yolo`) with approval checkpoints.
- Browser flow orchestration for multi-step form filling and submission.
- Human handoff for CAPTCHA and other non-automatable blocks.
- API + CLI + web interface support for both interactive and scripted usage.

## 3. System Architecture

### CLI Layer (`src/vulture/cli/app.py`)
- Entry-point commands for initialization, profile management, run lifecycle, job listing, and serving the web/API app.
- Uses `SessionLocal` and `Repository` for DB access, and `RunOrchestrator` for workflow execution.

### API Layer (`src/vulture/api`)
- FastAPI routes under `/api` for profile, run, and job operations.
- Pydantic schemas define request/response contracts.
- Includes WebSocket event stream support for run updates.

### Web UI Layer (`src/vulture/web`)
- Server-rendered Jinja templates and static CSS.
- HTMX-enabled dashboard and run-detail views.
- Suitable for local operations and approval handling.

### Orchestration Layer (`src/vulture/core/orchestrator.py`)
- Coordinates run stages:
  - job parsing
  - document tailoring
  - profile patching
  - browser flow execution
  - completion/failure state transitions
- Emits run events and enforces mode-specific approval policy.

### LLM Routing Layer (`src/vulture/llm/router.py`)
- Routes task categories (`extract`, `writer`, `db_patch`, etc.) to configured providers.
- Falls back between OpenAI and local providers based on config and runtime availability.
- Includes heuristic fallbacks when structured model output is unavailable.

### Persistence Layer (SQLite + SQLAlchemy)
- SQLAlchemy models in `src/vulture/db/models.py`.
- Repository access patterns in `src/vulture/db/repositories.py`.
- Alembic migrations under `alembic/`.

## 4. Repository Structure

```text
Vulture/
  alembic/                     # DB migrations
  src/vulture/
    api/                       # FastAPI routes, schemas, app wiring
    browser/                   # Browser automation adapters and engine
    cli/                       # Typer CLI commands
    core/                      # Orchestrator, modes, runtime event bus
    db/                        # SQLAlchemy models, session, repositories, seeding
    llm/                       # Provider pool, prompts, router
    web/                       # Jinja templates and static assets
    config.py                  # Environment-backed settings
    main.py                    # Script/CLI entry module
  tests/                       # Unit/integration/e2e test suite
  .env.example                 # Example runtime configuration
  pyproject.toml               # Packaging, dependencies, tooling
  README.md                    # Project documentation
  LICENSE                      # CC BY-NC 4.0 legal text
```

## 5. Requirements and Prerequisites

- Python `3.11+`
- `pip`
- SQLite (included with standard Python builds)
- Optional for hybrid routing:
  - OpenAI API access
  - Local OpenAI-compatible endpoint (for example Ollama-compatible API)

Recommended OS prerequisites for browser automation:
- System dependencies required by your browser automation stack.
- A desktop session if running non-headless browser mode.

## 6. Installation and Environment Setup

```bash
cd /Users/subhajitrouy/Documents/Github/Vulture
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

Initialize local data directories and database:

```bash
vulture init
```

## 7. Configuration Guide

Vulture reads configuration from environment variables (`.env` by default). Key groups:

### Runtime and App
- `APP_NAME`, `APP_ENV`, `APP_HOST`, `APP_PORT`
- `TIMEZONE`, `LOG_LEVEL`, `SECRET_KEY`

### Data and Storage
- `DATABASE_URL`
- `DATA_DIR`, `UPLOAD_DIR`, `RESUME_DIR`, `COVER_LETTER_DIR`, `RUN_ARTIFACT_DIR`

### Browser Automation
- `BROWSER_USE_HEADLESS`
- `BROWSER_USE_KEEP_BROWSER_OPEN`
- `BROWSER_USE_MAX_STEPS`
- `BROWSER_USE_NAV_TIMEOUT_SEC`, `BROWSER_USE_ACTION_TIMEOUT_SEC`
- `BROWSER_USE_ALLOWED_DOMAINS`, `BROWSER_USE_BLOCKED_DOMAINS`
- `BROWSER_USE_USER_DATA_DIR`

### LLM and Providers
- OpenAI:
  - `OPENAI_API_KEY`, `OPENAI_BASE_URL`
  - `OPENAI_MODEL_PLANNER`, `OPENAI_MODEL_EXTRACTOR`, `OPENAI_MODEL_WRITER`
  - `OPENAI_TIMEOUT_SEC`
- Local provider:
  - `LOCAL_LLM_ENABLED`, `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_API_KEY`
  - `LOCAL_LLM_MODEL`, `LOCAL_LLM_TIMEOUT_SEC`
- Router controls:
  - `LLM_ROUTER_DEFAULT`
  - `LLM_ROUTER_PLAN_PROVIDER`
  - `LLM_ROUTER_EXTRACT_PROVIDER`
  - `LLM_ROUTER_DB_PATCH_PROVIDER`
  - `LLM_ROUTER_WRITER_PROVIDER`

### Policy and Safety
- `DEFAULT_RUN_MODE`
- `STRICT_APPROVAL_POLICY`, `MEDIUM_APPROVAL_POLICY`, `YOLO_APPROVAL_POLICY`
- `REQUIRE_CAPTCHA_HANDOFF`, `AUTO_SUBMIT_ENABLED`
- `MAX_RETRIES_PER_FIELD`, `MAX_RETRIES_PER_PAGE`
- `SAVE_SCREENSHOTS`, `SAVE_DOM_SNAPSHOTS`
- `PII_ENCRYPTION_KEY`, `REDACT_LOG_PII`, `AUDIT_RETENTION_DAYS`

### Web/API Exposure
- `WEB_UI_ENABLED`
- `API_AUTH_MODE`, `SESSION_TTL_MIN`
- `CORS_ORIGINS`

## 8. Running the App

Start the local server (web + API):

```bash
source .venv/bin/activate
vulture serve --host 127.0.0.1 --port 8787
```

Open:
- Dashboard: `http://127.0.0.1:8787/`
- Health check: `http://127.0.0.1:8787/health`

## 9. CLI Command Reference

### Initialization

```bash
vulture init
```

Initializes database schema, required directories, and seed records.

### Profile Commands

Create profile:

```bash
vulture profile create --name "Main" --job-family "Engineering" --summary "Backend-focused"
```

Import profile from JSON file:

```bash
vulture profile import --file ./profile.json
```

Add or update an answer for a profile:

```bash
vulture profile add-answer \
  --profile-id 1 \
  --question "Are you authorized to work in the US?" \
  --answer "Yes" \
  --question-type work_auth
```

### Run Commands

Start an application run:

```bash
vulture apply --url "https://example.com/jobs/123" --profile 1 --mode medium --submit
```

Inspect run status and events:

```bash
vulture run status --run-id 1
```

Approve a pending approval event:

```bash
vulture run approve --run-id 1 --event-id 10
```

Reject a pending approval event:

```bash
vulture run reject --run-id 1 --event-id 10
```

### Job Commands

List recently tracked jobs:

```bash
vulture jobs list --limit 20
```

### Server Command

```bash
vulture serve --host 127.0.0.1 --port 8787
```

## 10. API Reference

All JSON API routes are under `/api`.

### Profile APIs
- `POST /api/profiles`
  - Create a new profile.
- `GET /api/profiles`
  - List profiles.
- `POST /api/profiles/{profile_id}/answers`
  - Add/update a profile answer.

### Job Intake API
- `POST /api/jobs/intake`
  - Ingest job URL and run analysis.

### Run APIs
- `POST /api/runs`
  - Create a new run.
- `GET /api/runs/{run_id}`
  - Get run state.
- `POST /api/runs/{run_id}/approve`
  - Approve an event.
- `POST /api/runs/{run_id}/reject`
  - Reject an event.
- `GET /api/runs/{run_id}/events`
  - List run events.
- `WS /api/runs/{run_id}/stream`
  - Subscribe to run event stream.

### General
- `GET /health`
  - Liveness/status check.

## 11. Run Modes and Approval Flow

### `strict`
- Highest human oversight.
- Approval expected at each major step/action.

### `medium`
- Approval at stage boundaries.
- Balances autonomy and control.

### `yolo`
- Maximum autonomy.
- Continues automatically except required human interventions (for example CAPTCHA).

### Approval Behavior
- Runs enter waiting states when approval is required.
- User can resume or block progression through approve/reject operations.
- Rejected approvals move runs to blocked state.

## 12. Data Persistence and Artifacts

Default local storage is under `./data`.

Primary persisted data:
- SQLite DB: run metadata, profiles, question bank, events, and suggestions.
- Generated documents:
  - `data/resumes/`
  - `data/cover_letters/`
- Run and browser artifacts:
  - `data/runs/`
  - optional screenshots / snapshots depending on config.

Notes:
- This repository's `.gitignore` excludes runtime data (`data/`, DB files, `.env`, virtualenv artifacts).
- Generated artifacts are local operational state, not source-controlled project code.

## 13. Testing and Quality Checks

Run full test suite:

```bash
source .venv/bin/activate
pytest -q
```

Run specific test groups:

```bash
pytest -q tests/unit
pytest -q tests/integration
pytest -q tests/e2e
```

Optional style/lint checks (if configured in your workflow):

```bash
ruff check .
```

## 14. Operational Notes and Limitations

- CAPTCHA requires human intervention; Vulture will not bypass it.
- If required profile answers are missing, runs pause/block instead of fabricating facts.
- Browser automation depends on target site behavior; selectors and flows may require tuning.
- LLM output quality depends on model/provider reliability and prompt-context quality.
- Current setup is local-first and suited to controlled environments; production hardening (auth, secret management, observability, scaling) must be added separately.
- Security-sensitive deployments should review PII handling, encryption settings, and retention policies before use.

## 15. License

This project is licensed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.

See `/Users/subhajitrouy/Documents/Github/Vulture/LICENSE` for the full legal text.

Human-readable summary: [https://creativecommons.org/licenses/by-nc/4.0/](https://creativecommons.org/licenses/by-nc/4.0/)
