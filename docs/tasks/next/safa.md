# Safa: next tasks

**Branch:** create `safa/insights` from the latest `main`. **Files:** `memory/`, `backend/routers/insights.py`, `frontend/static/insights.html`, `frontend/static/insights.js`, `tests/`.

## Done (merged)
Decisions, gate results, metrics, `log_ingest.py`, tests, a detailed Bob session with screenshots. The orchestrator records into your modules live (`orchestrator/recorder.py`), so the numbers come from real runs.

## To do, in order

1. **Insights endpoints** in `backend/routers/insights.py` (a FastAPI `APIRouter`): `GET /projects/{id}/decisions`, `/gates`, `/metrics` (with `impact_text`), `/tests`, `/security` (the last two from `logs/orchestrator.jsonl`). Shapes: `docs/API.md`. Tell Manar so he includes the router in `backend/main.py` with one line, and add `tests/test_api_insights.py`.
2. **Insights screen** (`insights.html`, `insights.js`): decision log, gate results, test runs, security runs and the Impact panel. Real numbers only. Ask Fati for a link from the main page.
3. **Impact wording**, honest and measured: "1 access-control bug (CWE-639) caught two independent ways (tests and security scan), fixed by the Debugger, tests 17/20 to 20/20, 2 retries, 2 human approvals by design". Do not claim more. Write it in `docs/IMPACT.md` with how each number was measured.
4. **Clean runs:** delete `logs/orchestrator.jsonl`, run `python scripts/demo.py --auto-approve --pause 0` three times, and give the Leader the numbers.
5. **Demo:** explain memory and the Impact numbers in 30 seconds.

## Done when
The Insights page shows real data after a run, the numbers match the slide, and tests pass.

## Talk to
Manar (router), Fati (link), Leader (numbers for the slide).
