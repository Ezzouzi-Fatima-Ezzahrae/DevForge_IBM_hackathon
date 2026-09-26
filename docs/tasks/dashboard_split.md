# Dashboard: work split (Ali's work shared)

Goal: a live dashboard for the demo, in about 90 minutes. Simple and honest: plain HTML, CSS and JavaScript served by FastAPI (no Next.js, no build step, no PostgreSQL). The contract is in `docs/API.md`. Each person owns separate files, so nobody conflicts.

## Everything Ali was assigned

1. API skeleton with the endpoints, CORS
2. Real endpoints for start and status
3. Read decisions, metrics, gate results, test runs, security runs
4. Approval endpoint that unblocks the run
5. Pipeline screen (live)
6. Approval screen
7. Decision log and Impact screen
8. How to run it, Bob evidence
9. Testing the whole flow

## Who does what

| Person | Owns (only these files) | Work | Done when |
|---|---|---|---|
| **Manar** | `backend/main.py`, `backend/runs.py`, `backend/routers/projects.py`, `tests/test_api_projects.py`, `requirements.txt` (add `uvicorn`, `fastapi`, `httpx` if missing) | 1, 2, 4 and the status endpoint: create project, start the pipeline in a background thread with `run_pipeline(..., approval_fn=broker.wait)` (the Leader provides `orchestrator/approval_broker.py`), build the `stages`, `events` and `awaiting_approval` fields of `/status` from `data/project_state.json` and `logs/orchestrator.jsonl`, approve and reset endpoints, CORS, serve `frontend/static/` at `/`. Include the insights router if it exists. | `uvicorn backend.main:app` starts; `curl` create, start, status shows the stages moving; tests with `TestClient` |
| **Safa** | `backend/routers/insights.py`, `frontend/static/insights.html`, `frontend/static/insights.js`, `tests/test_api_insights.py` | 3 and 7: decisions, gates, metrics (with the exact honest Impact wording), tests and security runs from the log; the Insights screen | The Insights page shows real data after a run and matches `docs/API.md` |
| **Fati** | `frontend/static/index.html`, `frontend/static/pipeline.js`, `frontend/static/style.css` | 5 and 6: the Pipeline screen and the Approval panel, following `docs/DEMO_PLAN.md` (clear cards, colours, retry badges, "stub" labels, red FAILED banner, Approve buttons, Start and Reset buttons) | A full run is visible live from start to RELEASED, and Approve unblocks it |
| **Leader** | `orchestrator/approval_broker.py`, `orchestrator/runner.py`, `orchestrator/approval.py` | 4 (the orchestrator side): a thread-safe approval broker with a timeout, `approval_fn` argument in `run_pipeline`, the terminal approval still works | Approve and Request-changes from the API both work; tests |
| **Ali** (if he is back) | `docker-compose.yml`, README section "Run the dashboard", `bob_sessions/ali_builder_session.md` | 8 and 9, then review and polish: run the whole flow, report bugs to the owner | End-to-end test done; Bob evidence filled |

If Ali already has working code, tell the Leader now: his files replace the matching row (same contract).

## Order and integration points

1. **Now (10 min):** everyone reads `docs/API.md`. Fati can start with a fake JSON response, Manar with the routes, Safa with her endpoints.
2. **About 40 min:** Leader delivers `approval_broker.py`. Manar's backend runs with it.
3. **About 60 min:** Fati points the screen at the real API; Safa's Insights page shows real data.
4. **About 90 min:** full flow test with the whole team: Start, watch the loops, Approve, RELEASED.

## Rules

- Only edit your own files. If you need a change in someone else's file, ask them.
- Open a PR as soon as your part works (even partly). Pull `main` before you start and before your PR.
- Real data only. Steps that still use a stub (build, fix) are labelled "stub".
- Do not commit `backend/demo_bug.py` in its fixed state. Run `python tests/restore_demo_bug.py` before each run (the Reset button does it).
