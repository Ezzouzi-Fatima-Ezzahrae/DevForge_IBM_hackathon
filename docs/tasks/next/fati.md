# Fati: next tasks

**Branch:** create `fati/dashboard` from the latest `main`. **Files:** `frontend/static/` only (plus `DATA_SOURCES.md`, `fixtures/` if you touch them).

## Done (merged)
`PlanAgent` (a `BaseAgent`, registered as the `plan` stage, reports real duration, gate tests), `DATA_SOURCES.md` with sources, Bob evidence (PR merged).

## To do, in order

1. **The dashboard page** (the main open item). The backend already serves `frontend/static/` at `/` and every endpoint exists; the contract is `docs/API.md`.
   - `index.html`, `pipeline.js`, `style.css`: one card per stage (`state`: pending, running, done, failed), verdict, summary, duration, retry badges from `retries`, a **"stub" label** when `real` is false, a live event list, a red "Needs human attention" banner when `status` is `FAILED`.
   - An **approval panel** when `awaiting_approval` is not null: show `gate_results`, a button Approve and a button Request changes, calling `POST /projects/{id}/approve` with `{"gate": awaiting_approval.gate, "approved": true|false}`.
   - **Start** (creates a project with `POST /projects`, then `/start`) and **Reset** buttons. Poll `GET /projects/{id}/status` every 2 seconds.
   - Try it: `pip install -r requirements.txt`, then `uvicorn backend.main:app --port 8000` from the repository root, and open `http://localhost:8000`.
   - Safa adds an Insights section (`insights.html`); leave her a link to it.
2. **Second saved plan** (optional): `fixtures/plan_output_<name>.json`, picked by keyword, so the demo does not look hard-coded.
3. **Demo:** be ready to explain the planning step in 30 seconds.

## Done when
A full run is visible live from Start to RELEASED, and Approve unblocks it, on a fresh clone.

## Talk to
Manar (API), Safa (Insights section), Leader (approval flow).
