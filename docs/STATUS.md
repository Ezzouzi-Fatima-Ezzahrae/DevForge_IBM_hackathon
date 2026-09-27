# Project status

Updated 27 Sep 2026, about 02:00. Everything marked "verified" was checked on a **fresh clone of `main`**: clean install from `requirements.txt`, `python -m pytest -q` (128 passed), `scripts/demo.py` twice in a row (RELEASED, 17/20 to 20/20, identical both times), the CLI, the stub fallback, and the API driven with curl from create to RELEASED.

## Summary

| Area | Owner | Status | Notes |
|---|---|---|---|
| Architecture, contracts | Leader | Done, verified | `docs/ARCHITECTURE.md`, `docs/agent_contracts.md`, `orchestrator/contracts.py` |
| Orchestrator (state machine, gates, runner, logging, CLI) | Leader | Done, verified | Parallel tests and security, retries, FAILED escalation |
| Approval broker (approve or reject from the API) | Leader | Done, verified | `orchestrator/approval_broker.py`; timeout counts as a rejection |
| Gate tests | Leader | Done | `tests/test_gates.py` (also fixed: 0 tests no longer passes the tests gate) |
| Offline terminal demo | Leader | Done, verified | `python scripts/demo.py` |
| README with diagram, slides | Leader | Done | `README.md`, `DevForge_Slides.pptx` |
| Memory and metrics wiring | Leader | Done, verified | `orchestrator/recorder.py` |
| Plan agent | Fati | Done, connected | Replays a saved Bob Plan session (no live AI call). Fallback: `DEVFORGE_PLAN_AGENT_MODE=stub` |
| Testing agent, Debug agent | Manar | Done, connected, verified | Real pytest; the debug agent really patches the file |
| Backend API | Manar | Done, verified | `POST /projects`, `/start`, `GET /status`, `POST /approve`, `/reset`. Runs the real pipeline to RELEASED |
| Security agent, gate | Haytam | Done, connected | Finds the ownership bug (HIGH, CWE-639) and the hard-coded secret (LOW) |
| Fix agent | Haytam | **Open** | Still a stub. The security gate passes only because the Debugger already fixed the ownership bug |
| Memory and metrics | Safa | Merged | Insights endpoints, Impact wording and `docs/IMPACT.md` still open |
| Dashboard page | Fati | **Open** | Backend serves `frontend/static/` but it does not exist yet: `/` returns 404. Terminal demo is the fallback |
| Insights endpoints and screen | Safa | **Open** | `docs/API.md` |
| Bob evidence | Everyone | Files present for all members | Check each file has the task, the Bob features used and readable screenshots |
| Demo rehearsals, backup video | Everyone | **Open** | `docs/DEMO_PLAN.md` |

## What is real and what is simulated

Real: orchestrator, gates, retries, parallel checks, approval, testing agent, debug agent, security agent, backend API, memory and metrics.
Simulated: plan agent (replays a saved Bob plan), build agent and fix agent (stubs).

## Known limits

1. **One project at a time in the API.** The state file holds a single project; creating a second one while the first is running hides the first. Fine for the demo.
2. **Running the pipeline by hand patches `backend/demo_bug.py`.** `scripts/demo.py` and the API restore the bug automatically. After a manual `python -m orchestrator.run`, run `python tests/restore_demo_bug.py`. Never commit the fixed version.
3. **Security fix is a stub.** Do not say the fix agent fixed anything in the presentation. The Debugger fixed the access-control bug; the scanner then finds nothing to block.
4. **The hard-coded secret is rated LOW** by the scanner, so it is reported but does not block the gate.
5. **Some of Manar's tests overlap** (three tests around the same delete case). It works.

## Decisions taken

- State and memory are stored in files (`data/project_state.json`, `memory/data/*.json`), not PostgreSQL.
- The dashboard is plain HTML served by FastAPI, not Next.js.
- Real agents are registered with a fallback to the stub.
- The demo app is `backend/demo_bug.py`: bug 1 = missing ownership check (found by tests and by the scanner, fixed by the Debugger); bug 2 = hard-coded secret (reported as LOW).

## Next

Round-2 tasks per person: `docs/tasks/next/<name>.md` and `docs/tasks/dashboard_split.md`. Demo script: `docs/DEMO_PLAN.md`. Final checks: `docs/SUBMISSION_CHECKLIST.md`.
