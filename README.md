# Vulture

Vulture is a local-first autonomous job application assistant. It parses a job posting URL, tailors documents, applies profile patch suggestions, and executes browser automation with configurable approval gates.

## 1. Core Features

- Local SQLite profile + run history storage.
- CLI, JSON API, and web dashboard.
- Hybrid LLM routing (OpenAI + local OpenAI-compatible providers).
- Browser automation with human approval checkpoints.
- LinkedIn Easy Apply MVP path with automatic platform detection.
- Human handoff for CAPTCHA and other anti-bot gates.

## 2. Repository Layout

```text
Vulture/
  alembic/                     # DB migrations
  src/vulture/
    api/                       # FastAPI routes and schemas
    browser/                   # Browser automation engine/adapters
    cli/                       # Typer CLI
    core/                      # Run orchestration and runtime events
    db/                        # SQLAlchemy models/repositories/init
    llm/                       # Provider routing and prompts
    web/                       # HTMX/Jinja dashboard
  tests/                       # Unit/integration/e2e tests
  .env.example                 # Example runtime config
  README.md
```

## 3. Prerequisites

- Python 3.11+
- pip
- SQLite (bundled with standard Python)
- Browser runtime dependencies used by `browser-use`

Optional provider requirements:

- OpenAI API key for OpenAI routes
- A local OpenAI-compatible endpoint for local routes (for example Ollama-compatible API)

## 4. Quick Start

```bash
cd /Users/subhajitrouy/Documents/Github/Vulture
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

Initialize directories + database:

```bash
vulture init
```

## 5. Browser Runtime Setup (`browser-use`)

Install browser runtime once in your environment:

```bash
python -m playwright install chromium
```

If your shell cannot find `playwright` through `python -m`, install Playwright first in the same virtualenv and rerun.

## 6. Configuration Guide

Vulture reads settings from environment variables (`.env` by default).

### 6.1 Required Baseline Variables (minimum)

- `APP_HOST`, `APP_PORT`
- `DATABASE_URL`
- `DATA_DIR`, `RESUME_DIR`, `COVER_LETTER_DIR`, `RUN_ARTIFACT_DIR`
- `BROWSER_USE_USER_DATA_DIR`

### 6.2 Provider/API Setup Matrix

#### OpenAI-only

```env
OPENAI_API_KEY=sk-...
LOCAL_LLM_ENABLED=false
LLM_ROUTER_DEFAULT=openai
LLM_ROUTER_PLAN_PROVIDER=openai
LLM_ROUTER_EXTRACT_PROVIDER=openai
LLM_ROUTER_DB_PATCH_PROVIDER=openai
LLM_ROUTER_WRITER_PROVIDER=openai
```

#### Local-only

```env
OPENAI_API_KEY=
LOCAL_LLM_ENABLED=true
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=qwen2.5:14b-instruct
LLM_ROUTER_DEFAULT=local
LLM_ROUTER_PLAN_PROVIDER=local
LLM_ROUTER_EXTRACT_PROVIDER=local
LLM_ROUTER_DB_PATCH_PROVIDER=local
LLM_ROUTER_WRITER_PROVIDER=local
```

#### Hybrid (recommended default shape)

```env
OPENAI_API_KEY=sk-...
LOCAL_LLM_ENABLED=true
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=qwen2.5:14b-instruct
LLM_ROUTER_DEFAULT=hybrid
LLM_ROUTER_PLAN_PROVIDER=openai
LLM_ROUTER_EXTRACT_PROVIDER=openai
LLM_ROUTER_DB_PATCH_PROVIDER=local
LLM_ROUTER_WRITER_PROVIDER=openai
```

### 6.3 Common Runtime and Safety Variables

```env
DEFAULT_RUN_MODE=medium
STRICT_APPROVAL_POLICY=action
MEDIUM_APPROVAL_POLICY=stage
YOLO_APPROVAL_POLICY=captcha_only
REQUIRE_CAPTCHA_HANDOFF=true
AUTO_SUBMIT_ENABLED=true
SAVE_SCREENSHOTS=true
SAVE_DOM_SNAPSHOTS=false
```

### 6.4 Web/API Exposure

```env
WEB_UI_ENABLED=true
API_AUTH_MODE=local_session
SESSION_TTL_MIN=720
CORS_ORIGINS=http://127.0.0.1:8787
```

## 7. LinkedIn Easy Apply MVP Setup

LinkedIn support is auto-detected from `linkedin.com` job URLs. No extra CLI/API flag is required.

### 7.1 Session Strategy (no credential storage)

Vulture does **not** store LinkedIn username/password. It reuses a persistent browser profile directory.

Set a stable profile path:

```env
BROWSER_USE_USER_DATA_DIR=./data/browser_profile
```

### 7.2 One-time LinkedIn Login Bootstrap

1. Start a run in non-headless mode (`BROWSER_USE_HEADLESS=false`).
2. Manually sign in to LinkedIn in the opened browser once.
3. Keep `BROWSER_USE_USER_DATA_DIR` unchanged for future runs.

### 7.3 Expected LinkedIn MVP Behavior

- For Easy Apply postings: Vulture uses a LinkedIn-specific browser flow.
- If posting is not Easy Apply or redirects to external apply: run transitions to `blocked` with an actionable event message.
- CAPTCHA/human verification: run transitions to `waiting_captcha` until approved/resumed.

## 8. Running the App

Start web + API server:

```bash
source .venv/bin/activate
vulture serve --host 127.0.0.1 --port 8787
```

URLs:

- Dashboard: `http://127.0.0.1:8787/`
- Swagger UI: `http://127.0.0.1:8787/docs`
- ReDoc: `http://127.0.0.1:8787/redoc`
- Health: `http://127.0.0.1:8787/health`

## 9. CLI Reference

Initialize:

```bash
vulture init
```

Run with the profile created in this setup (`profile_id=1`, name `Main`):

```bash
cd /Users/subhajitrouy/Documents/Github/Vulture
source .venv/bin/activate

# one-time bootstrap: sign in to LinkedIn using the same persistent browser profile
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="/Users/subhajitrouy/Documents/Github/Vulture/data/browser_profile" \
  --profile-directory="Default" \
  "https://www.linkedin.com/login"

# then run Vulture with the created profile
vulture apply \
  --url "https://www.linkedin.com/jobs/collections/easy-apply/?currentJobId=4370656199&discover=recommended&discoveryOrigin=JOBS_HOME_JYMBII" \
  --profile 1 \
  --mode yolo \
  --submit
```

Check run status/events:

```bash
vulture run status --run-id <run_id>
```

Create profile:

```bash
vulture profile create --name "Main" --job-family "Engineering" --summary "Backend-focused"
```

Add answer:

```bash
vulture profile add-answer \
  --profile-id 1 \
  --question "Are you legally authorized to work in the United States?" \
  --answer "Yes" \
  --question-type work_auth
```

Start run:

```bash
vulture apply --url "https://www.linkedin.com/jobs/view/123456789" --profile 1 --mode medium --submit
```

Run status:

```bash
vulture run status --run-id 1
```

Approve/reject pending event:

```bash
vulture run approve --run-id 1 --event-id 10
vulture run reject --run-id 1 --event-id 10
```

## 10. API Reference

All JSON endpoints are under `/api`.

### 10.1 Profile APIs

- `POST /api/profiles`
- `GET /api/profiles`
- `POST /api/profiles/{profile_id}/answers`
- `POST /api/profiles/{profile_id}/cv/import`
- `GET /api/profiles/{profile_id}/questionnaire`
- `GET /api/profiles/{profile_id}/questionnaire/review`
- `POST /api/profiles/{profile_id}/questionnaire/{question_hash}/verify`
- `POST /api/profiles/{profile_id}/questionnaire/{question_hash}/reject`
- Additional profile sections (education, experience, skills, publications, awards, conferences, teaching, service, additional projects)

### 10.2 Job + Run APIs

- `POST /api/jobs/intake`
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/runs/{run_id}/approve`
- `POST /api/runs/{run_id}/reject`
- `GET /api/runs/{run_id}/events`
- `WS /api/runs/{run_id}/stream`

## 11. End-to-End cURL Workflow

Set base URL:

```bash
BASE_URL="http://127.0.0.1:8787"
```

### 11.1 Create profile

```bash
curl -sS -X POST "$BASE_URL/api/profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main",
    "job_family": "Engineering",
    "summary": "Backend engineer focused on APIs and distributed systems"
  }'
```

### 11.2 Add key answer (work authorization)

```bash
curl -sS -X POST "$BASE_URL/api/profiles/1/answers" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Are you legally authorized to work in the United States?",
    "answer": "Yes",
    "question_type": "work_auth"
  }'
```

### 11.3 Create LinkedIn run (contract unchanged)

```bash
curl -sS -X POST "$BASE_URL/api/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.linkedin.com/jobs/view/123456789",
    "profile_id": 1,
    "mode": "medium",
    "submit": false
  }'
```

### 11.4 Read run events

```bash
curl -sS "$BASE_URL/api/runs/1/events"
```

### 11.5 Approve/reject pending event

```bash
curl -sS -X POST "$BASE_URL/api/runs/1/approve" \
  -H "Content-Type: application/json" \
  -d '{"event_id": 10}'

curl -sS -X POST "$BASE_URL/api/runs/1/reject" \
  -H "Content-Type: application/json" \
  -d '{"event_id": 10}'
```

## 12. Run Modes

- `strict`: approvals at all major steps.
- `medium`: approvals at key stage boundaries.
- `yolo`: only mandatory interventions (for example CAPTCHA).

## 13. Data and Artifacts

Default runtime data is stored under `./data`:

- `data/vulture.db`
- `data/resumes/`
- `data/cover_letters/`
- `data/runs/`
- `data/browser_profile/` (session persistence)

## 14. Testing

Run all tests:

```bash
source .venv/bin/activate
pytest -q
```

Run focused groups:

```bash
pytest -q tests/unit
pytest -q tests/integration
pytest -q tests/e2e
```

## 15. Troubleshooting

### LinkedIn session expired

- Symptom: LinkedIn flow stops early or blocks unexpectedly.
- Fix: run non-headless, sign in manually again, keep same `BROWSER_USE_USER_DATA_DIR`.

### Run status becomes `blocked`

Common reasons:

- LinkedIn posting is external apply / not Easy Apply.
- LinkedIn flow could not verify required action marker.
- Critical required data could not be completed safely.

Inspect:

```bash
vulture run status --run-id <id>
```

Or via API:

```bash
curl -sS "$BASE_URL/api/runs/<id>/events"
```

### Missing provider/API key

- OpenAI route selected but `OPENAI_API_KEY` is empty.
- Local route selected but local endpoint/model unavailable.

Fix by aligning `LLM_ROUTER_*` variables with enabled providers.

### Browser runtime not installed

- Symptom: browser tasks fall back to dry-run behavior.
- Fix: install browser runtime with `python -m playwright install chromium`.

## 16. License

This project is licensed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.

- License file: `/Users/subhajitrouy/Documents/Github/Vulture/LICENSE`
- Summary: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
