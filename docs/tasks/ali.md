# Ali — Full-Stack Lead

## Role
Full-stack lead. Build the visible platform judges will see: the dashboard and the backend API.

## Branch and Folders
- **Branch:** `ali/platform`
- **Folders:** `frontend/`, `backend/`

---

## Objective
Build the platform layer that makes DevForge real to a judge in 30 seconds. The dashboard must show the live pipeline state. The backend must persist project state and serve all agent results.

---

## Context
DevForge orchestrates: **Idea → Research → Requirements → Architecture → Milestones → Build → Test → Debug → Security → Human Approval → Release**.
Demo app: a simple task-management SaaS. Stack: **Next.js + TypeScript + Tailwind** (frontend), **FastAPI + PostgreSQL** (backend), **Docker Compose** (local env). Do not expand the stack.

Every agent returns:
```json
{ "agent": "...", "status": "PASS | FAIL | ERROR", "summary": "...", "data": {}, "duration_seconds": 0, "timestamp": "..." }
```

---

## Deliverables

- [ ] **Next.js dashboard skeleton** with these pages: Project Overview, Requirements, Architecture, Milestones, Agent Activity, Testing, Security, Decision Memory, Release.
- [ ] **Live Project Pipeline screen** — the most important screen. Shows each stage (Research, Requirements, Architecture, Build, Test, Debug, Security, Release) with one of three states: ✅ done / ⚙ in-progress / ○ pending. Fake data is fine at first; it must update live from `GET /projects/{id}/status` once the backend is ready.
- [ ] **FastAPI backend skeleton** with PostgreSQL wired in Docker Compose (`docker-compose up` must start everything).
- [ ] **These endpoints only** (no more than needed for the demo):
  - `POST /projects` — create a project
  - `POST /projects/{id}/start` — start the pipeline
  - `GET /projects/{id}/status` — current state (pipeline page polls this every 3 s)
  - `GET /milestones` — list milestones
  - `GET /tests` — test results for a milestone
  - `GET /security` — security findings for a milestone
  - `GET /decisions` — decision log
- [ ] **Bob evidence:** `bob_sessions/ali_task01_frontend.png` and `bob_sessions/ali_task02_backend.png`.

---

## Dependencies

| Depends on | What you need |
|---|---|
| **Leader** | Orchestrator calls `POST /projects/{id}/start`; agree on the status response shape before hour 4 |
| **Manar** | Test result JSON shape (`GET /tests` must match what Manar's agent outputs) |
| **Haytam** | Security finding JSON shape (`GET /security` must match what Haytam's agent outputs) |
| **Safa** | Decision and metrics shape (`GET /decisions` and future `/metrics` endpoint) |

---

## Bob Task
Use **Bob Agent mode** to scaffold the frontend and backend.
1. Run the prompt below to generate the Next.js skeleton.
2. Screenshot the Bob session → save as `bob_sessions/ali_task01_frontend.png`.
3. Run a second session for the FastAPI backend → save as `bob_sessions/ali_task02_backend.png`.

---

## Definition of Done
- [ ] `docker-compose up` starts the API on `:8000` and the database with no errors.
- [ ] `npm run dev` starts the dashboard on `:3000` with no errors.
- [ ] The pipeline page loads and shows the stage list (fake data is acceptable).
- [ ] `GET /projects/{id}/status` returns a JSON object with at least `project_id` and `status`.
- [ ] Both Bob session screenshots saved in `bob_sessions/`.

---

## Deadline — First Sync (~hour 4)
Have the app running locally and the pipeline page returning any data from the status endpoint. Share your screen at the sync.

---

## Bob Prompt

```
You are an expert Next.js + TypeScript + Tailwind and FastAPI developer.

CONTEXT
Project: DevForge — an AI Software Development Lifecycle Orchestrator.
Demo app it will manage: a simple task-management SaaS.
Stack: Next.js 14 (App Router) + TypeScript + Tailwind CSS (frontend), FastAPI + PostgreSQL (backend), Docker Compose.

TASK
1. Scaffold a Next.js 14 App Router project with TypeScript and Tailwind already configured.
   Create these pages (each as app/<route>/page.tsx):
   - / (redirect to /pipeline)
   - /pipeline  ← MOST IMPORTANT: shows the live pipeline with stages
   - /requirements
   - /architecture
   - /milestones
   - /agent-activity
   - /testing
   - /security
   - /decisions
   - /release

2. For /pipeline, create a PipelineView component that renders a vertical list of stages:
   Research | Requirements | Architecture | Build | Test | Debug | Security | Release
   Each stage has a status badge: ✅ done / ⚙ in-progress / ○ pending.
   Use fake hard-coded data for now. The component must accept a `stages` prop.

3. Scaffold a FastAPI backend with these endpoints (stub implementations that return mock JSON):
   POST /projects
   POST /projects/{id}/start
   GET  /projects/{id}/status  → { "project_id": "...", "status": "planning | building | testing | done" }
   GET  /milestones
   GET  /tests
   GET  /security
   GET  /decisions

4. Write a docker-compose.yml that starts:
   - api service (FastAPI on port 8000)
   - db service (PostgreSQL 15, with POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB from .env)

CONSTRAINTS
- Do not add any library not in the stack above.
- No authentication for the demo.
- Keep files small and focused; one concern per file.
- Use TypeScript strict mode.

OUTPUT FORMAT
Provide the complete file tree first, then each file in full.
```
