# Ali: next tasks

**Branch:** `ali/platform`. **Folders:** `backend/`, `frontend/`.

## Status (reviewed)
**Nothing from you is on GitHub yet.** `backend/*` and `frontend/*` are still placeholders (`backend/demo_bug.py` belongs to Manar; do not change it). If you have work, **push it and open a Pull Request today, even partial.** The visible demo depends on you, and it is the largest missing part.

## Simplification
State and memory are in **files** (`data/project_state.json`, `memory/data/*.json`), not PostgreSQL. Do not spend time on a database.

## Tasks (in order)

1. **Push and PR** what you have.
2. **API skeleton with mock JSON** (FastAPI, `backend/main.py`), the 10 endpoints of `docs/ARCHITECTURE.md` section 12 (`POST /projects`, `POST /projects/{id}/start`, `GET /projects/{id}/status`, `POST /projects/{id}/approve`, `GET /milestones`, `GET /agents/results`, `GET /tests`, `GET /security`, `GET /decisions`, `GET /metrics`), with CORS for `http://localhost:3000`. Add a `requirements.txt` with `fastapi`, `uvicorn`, `pydantic`.
3. **Make three endpoints real:**
   - `POST /projects` creates an id and stores the idea.
   - `POST /projects/{id}/start` runs `from orchestrator.runner import run_pipeline` in a background task (with `auto_approve=True` until the Leader delivers the approval hook).
   - `GET /projects/{id}/status` returns `data/project_state.json`.
4. **Read the rest from files:** decisions `memory.memory_agent.query(project_id)`, metrics `memory.metrics.get_summary(project_id)`, gate results `query_gate_results(project_id)`, agent results from `logs/orchestrator.jsonl` (events `AGENT_DONE` and `GATE`).
5. **Dashboard, three screens:** `/pipeline` (stage cards PLAN, BUILD, TEST, DEBUG, SECURITY, FIX, APPROVAL, RELEASED with status, duration, retry badge; poll every 3 seconds), `/approval` (gate summary, Approve and Request Changes calling `POST /projects/{id}/approve`), `/decisions` (decision table plus the Impact panel with real numbers only).
6. **`FAILED` state:** show a red "Needs human attention" banner.
7. **Bob evidence:** fill `bob_sessions/ali_builder_session.md` (prompt, output, features, screenshots).

## Done when
`uvicorn` starts the API, the dashboard shows the pipeline updating live during a run, and Approve leads to RELEASED.

## Talk to
Leader (approval hook, state format), Safa (metrics and decisions functions), Manar and Haytam (result formats).

## Demo role
Ali drives the dashboard during the demo (start, pipeline, approval screen). Practice the click path until you can do it without looking. Also add a `package.json` with the start command and a short "how to run the dashboard" note in your PR. See `docs/DEMO_PLAN.md`. Feature freeze is at hour 40; after that only fix bugs that break a rehearsal.
