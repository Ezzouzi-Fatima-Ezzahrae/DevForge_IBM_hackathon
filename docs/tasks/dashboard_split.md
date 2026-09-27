# Dashboard: who builds what (current)

Goal: a live dashboard for the demo. Plain HTML, CSS and JavaScript served by FastAPI (no Next.js, no build step, no PostgreSQL). The contract is `docs/API.md`. Each person owns separate files.

| Person | Owns | Status |
|---|---|---|
| **Manar** | `backend/main.py`, `backend/runs.py`, `backend/routers/projects.py`, `tests/test_api_projects.py` | **Done and merged**: create, start (background thread), status (`stages`, `events`, `awaiting_approval`), approve, reset |
| **Leader** | `orchestrator/approval_broker.py`, `orchestrator/runner.py`, `tests/test_api_flow.py` | **Done and merged**: approval broker, wrong-gate check, API flow tests |
| **Fati** | `frontend/static/index.html`, `pipeline.js`, `style.css` | **Open**: pipeline screen and approval panel (`docs/tasks/next/fati.md`) |
| **Safa** | `backend/routers/insights.py`, `frontend/static/insights.html`, `insights.js`, `tests/test_api_insights.py` | **Open**: insights endpoints and screen (`docs/tasks/next/safa.md`) |

## Rules

- Only edit your own files. If you need a change in someone else's file, ask them.
- Open a PR as soon as your part works, even partly. Pull `main` before you start and before your PR.
- Real data only. Stages that still use a stub (build, fix) are labelled "stub".
- Never commit `backend/demo_bug.py` in its fixed state. The API restores the bug at every start.

## Fallback

If the page is not merged by the cut-off, the demo is the terminal version: `python scripts/demo.py`.
