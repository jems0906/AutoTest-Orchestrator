# AutoTest Orchestrator

<!-- Replace <owner>/<repo> with your GitHub repository path once initialized. -->
[![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/ci.yml)

A Python-based platform that plans, schedules, and tracks autonomous vehicle verification tests across simulation and hardware-in-the-loop style pipelines.

## What this project implements

- Requirements mapping and traceability matrix (`requirement -> test case -> scenario -> latest outcome`)
- Scenario generation for:
  - intersections
  - lane merges
  - pedestrian crossings
  - edge cases (sensor dropout, wrong-way actors, low friction)
- Simulated test execution pipeline with pass/fail, logs, and metrics persisted to PostgreSQL
- Coverage dashboard in React showing:
  - requirement coverage
  - regression trend
  - failure categories
  - test completeness
  - scenario diversity
  - open risk flags and coverage gaps
- Automation scheduler (nightly regression at 02:00 UTC) with risk-based retest flagging
- Analytics endpoints for coverage and prioritization decisions

## Stack

- Backend: FastAPI + SQLAlchemy (Python)
- Database: PostgreSQL
- UI: React dashboard (runtime CDN mode by default; optional Vite source included)
- Scheduler: APScheduler

## Project structure

```text
backend/
  app/
    analytics.py
    config.py
    database.py
    execution.py
    main.py
    models.py
    scenario_generator.py
    scheduler.py
    schemas.py
    seed.py
  reports/
  tests/
frontend/
  src/
docker-compose.yml
README.md
```

## Quick start (Docker)

1. From the project root:

```bash
docker compose up --build
```

2. Open the services:

- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:5173

The dashboard is served as static React runtime assets baked into the frontend image, so no frontend npm install or bind mount is required for Docker startup.

## Local development

### One-command local scripts (Windows PowerShell)

From project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-postgres.ps1
```

This is the recommended path and aligns with the target stack (PostgreSQL).

SQLite fallback (if Docker/PostgreSQL is unavailable):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-sqlite.ps1
```

Check status:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\status-local.ps1
```

Stop services:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop-local.ps1
```

### 1) Start PostgreSQL

Use Docker for DB only:

```bash
docker compose up -d postgres
```

The `start-local-postgres.ps1` script already does this automatically.

### 2) Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 3) Frontend

No build step required. Serve the static React dashboard directly:

```bash
cd frontend
python -m http.server 5173
```

Then open http://localhost:5173.

## Core API endpoints

- `GET /health`
- `GET /api/requirements`
- `POST /api/requirements`
- `GET /api/scenarios`
- `POST /api/scenarios/generate?scenario_type=<type>&count=<n>&seed=<seed>`
- `GET /api/test-cases`
- `POST /api/test-cases`
- `POST /api/runs/execute`
- `GET /api/runs`
- `GET /api/traceability`
- `GET /api/dashboard`
- `POST /api/scheduler/run-nightly`

## API authentication (optional RBAC)

Authentication is optional and disabled by default (`AUTH_ENABLED=false`).

When enabled, send API keys using the `X-API-Key` header:

- `VIEWER_API_KEY`: read-only endpoints
- `ENGINEER_API_KEY`: scenario generation, test creation, and execution endpoints
- `ADMIN_API_KEY`: scheduler trigger endpoint

Example:

```bash
curl -H "X-API-Key: <ENGINEER_API_KEY>" http://127.0.0.1:8000/api/dashboard
```

## Test validation

From `backend/`:

```bash
python -m pytest -q
```

This includes an end-to-end API flow test covering health, scenario generation, execution, traceability, and dashboard analytics.

## Database migrations (Alembic)

Migration configuration:

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/0001_initial_schema.py`

Run latest migration:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

Create a new migration after model metadata changes:

```bash
python -m alembic -c backend/alembic.ini revision --autogenerate -m "describe change"
```

Validate there is no remaining drift:

```bash
python -m alembic -c backend/alembic.ini check
```

## CI

GitHub Actions workflow:

- `.github/workflows/ci.yml`

What it validates on push and pull request:

- Backend dependency install and `pytest` run
- Dedicated RBAC authorization matrix test run
- Alembic migration upgrade check (`upgrade head`)
- Alembic schema drift check (`alembic check`)
- PR guard that fails if `backend/app/models.py` changes without a corresponding file in `backend/alembic/versions/`
- Backend API contract smoke checks for `/health`, `/api/dashboard`, and `/api/traceability`
- Static frontend asset checks (`index.html`, `app.js`, `styles.css`)
- Frontend HTTP smoke test using `python -m http.server`
- Full containerized stack smoke test (`docker compose up -d --build`) with backend and frontend endpoint verification
- Non-root backend runtime verification inside the containerized smoke test

Branch protection recommendations are documented in `.github/BRANCH_PROTECTION.md`.

## Deploy to Render

This repository includes a Render blueprint at `render.yaml` for:

- Managed PostgreSQL (`autotest-postgres`)
- Backend web service (`autotest-backend`) from `backend/Dockerfile`
- Frontend web service (`autotest-frontend`) from `frontend/Dockerfile`

Steps:

1. In Render, choose **New +** -> **Blueprint**.
2. Connect this GitHub repo.
3. Render will detect `render.yaml` and create all services.
4. After first deploy, open the frontend URL.

Important:

- The frontend reads `API_BASE` from environment at container startup.
- If your backend URL differs from `https://autotest-backend.onrender.com`, update the frontend service `API_BASE` env var in Render to:
  `https://<your-backend-service>.onrender.com/api`

## Data flow summary

1. Seed requirements/scenarios/test cases at startup.
2. Scenario generation adds new variations.
3. Test execution simulates runs and writes test results/logs/metrics.
4. High-risk failed scenarios create retest flags.
5. Dashboard aggregates SQL analytics for coverage, regressions, and gaps.
6. Scheduler queues nightly regression runs.

## Notes

- This implementation uses a deterministic simulation-style test runner (not a real vehicle simulator).
- `backend/reports/` receives JSON summaries for each test run.
- Extend `scenario_generator.py` with domain-specific parameters from your AV stack.
