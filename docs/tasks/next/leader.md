# Leader: next tasks

**Branch:** `leader/orchestrator`. **Folders:** `orchestrator/`, `docs/`, `config/`.

## Done
Architecture, contracts, orchestrator, tests, README, Bob evidence, status and next-task files.

## Tasks (in order)

1. **Review and merge**, in this order: Manar's PR (real testing and debug), Safa's fixes (`safae/memory`), then Haytam's and Ali's when they arrive. After each merge run `python -m pytest -q` on `main`.
2. **Restore the demo file before every run.** `backend/demo_bug.py` is patched by the debug agent. In demo mode `run_pipeline` should call `tests/restore_demo_bug.py` at the start, so a run is repeatable. Never commit the fixed file (check `git status`).
3. **Register Fati's PlanAgent** (after her update) as the `plan` stage.
4. **Fallback flags** in `config/orchestrator_config.json` (`"agents": {"plan": "real|stub", ...}`); in `agents_base.py` load real agents in try/except and fall back to the stub.
5. **Approval through the API:** make the approval function injectable in `run_pipeline` (with a timeout) for Ali's `POST /projects/{id}/approve`. Keep the CLI.
6. **Log the `auto` flag** in `HUMAN_APPROVAL` events, and add structured fields (counts, verdict) to the `GATE` events, so Safa's metrics do not parse text.
7. **Wire memory:** after the plan gate store the decisions (`memory_agent.store`); after every gate call `store_gate_result`; at the end of a run ingest the log.
8. **Real tests:** `tests/test_gates.py` is a placeholder; add a test for each gate and for `FAILED` after the retry limits.
9. **Demo script:** `scripts/demo.py`, offline stub demo under 2 minutes.
10. **Diagram** of the architecture and the state machine in `docs/`.
11. **Hour-24 sync:** each person demos, note the top 3 bugs, assign them. **Feature freeze at hour 40**, then rehearsals only.

## Done when
A fresh clone of `main` runs the full demo (real agents where ready, stubs elsewhere), the dashboard shows it live, and approval works from the dashboard.

## Also yours (nobody else owns these)

12. **Root `requirements.txt`** (pydantic, pytest, fastapi, uvicorn, httpx) and a short "how to run everything" section in `README.md`.
13. **Slides and script:** fill in `docs/DEMO_PLAN.md`, build the slides (problem, solution, architecture diagram, live demo, impact, how Bob was used), and ask each speaker for their 30-second text.
14. **Backup video** of a full successful run, recorded before the freeze.
15. **Stability:** 5 full runs in a row (restore `demo_bug.py` between runs) without a failure.
16. **Bob evidence check:** every member's `bob_sessions/*.md` is filled and readable.
17. **Fresh-clone test and submission:** follow `docs/SUBMISSION_CHECKLIST.md` on a clean clone of `main` and verify the format and deadline in the hackathon guide.
