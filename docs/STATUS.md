# Project status vs the plan

Updated 26 Sep 2026, evening. "Verified" means the code was read and its tests were run. "Not seen" means nothing is on `main` yet.

## Summary table

| Area | Owner | Status | Notes |
|---|---|---|---|
| Architecture, contracts | Leader | Done, verified | `docs/ARCHITECTURE.md`, `docs/agent_contracts.md`, `orchestrator/contracts.py` |
| Orchestrator (state machine, gates, runner, approval, logging, CLI) | Leader | Done, verified | 65 tests pass on the merged code; full demo run works |
| Orchestrator to backend, approval from the dashboard, fallback flags, memory wiring | Leader | **To do** | Needs Ali's endpoints |
| `tests/test_gates.py`, demo script, diagram | Leader | **To do** | `tests/test_gates.py` is still a placeholder |
| Plan agent | Fati | Merged, verified, **not connected** | Returns a saved Bob output; the orchestrator still uses the stub |
| Testing agent, Debug agent | Manar | Real, on her branch, verified by reading | Run real pytest; the debug agent really patches the file |
| Memory and metrics | Safa | First version merged; fixes on her branch | The fix "filter by project" is not in the merged code yet |
| Security agent, gate, fix | Haytam | **Not seen** | `security/*` are still one-line placeholders |
| Backend API | Ali | **Not seen** | `backend/*` are placeholders (only `demo_bug.py`, from Manar) |
| Dashboard | Ali | **Not seen** | `frontend/*` are placeholders |
| Bob evidence | Everyone | Partly done | Done: Leader, Safa, Fati, Manar. Empty: Ali, Haytam |

## Problems found in the review

1. **Running the pipeline changes a tracked file.** The debug agent patches `backend/demo_bug.py` for real. After a run, the repo shows that file as modified (bug fixed). Restore it with `python tests/restore_demo_bug.py` before every demo run and never commit the fixed version.
2. **The demo has two agents fixing the same bug.** The debug agent already adds the ownership check, so a real security agent scanning afterward finds nothing to block. Decision: plant a **second, different vulnerability** in `backend/demo_bug.py` for the security agent (a hard-coded secret, CWE-798). See `haytam.md` and `manar.md`.
3. **The plan agent is not connected.** `agents/plan_agent.py` is a plain function that reads `fixtures/plan_output.json`, and `agents_base.py` still registers the stub. Also its decisions carry a fixed `project_id` (`proj_task_management`) instead of the running project's id.
4. **Duplicate fixture locations.** `fixtures/plan_output.json` (real) and `tests/fixtures/plan_output.json` (empty). Use one.
5. **`DATA_SOURCES.md` is empty**, so research claims have no sources.
6. **Some of Manar's 20 tests are duplicates** (two of the three failing tests both delete task 1). It works, but judges may notice.
7. **Safa's `log_ingest.py` in the merged code still uses the first event's project and all events.** Her fix commit exists on her branch.
8. **Nothing calls memory or metrics from the orchestrator yet.**

## Decisions taken

- State and memory are stored in files (`data/project_state.json`, `memory/data/*.json`), not PostgreSQL.
- Real agents are registered with a fallback to the stub.
- The demo app is `backend/demo_bug.py`: bug 1 = missing ownership check (found by tests, fixed by the debug agent); bug 2 = hard-coded secret (found and fixed by the security agent).

## Timeline (from `docs/ARCHITECTURE.md`)

| Hours | Focus |
|---|---|
| 16-24 | First integration: orchestrator, backend and dashboard run one full pipeline |
| 24 | Mandatory 30-minute sync |
| 24-40 | Stabilize, real agents, polish, Bob evidence |
| 40 | **Feature freeze** |
| 40-48 | Demo rehearsal only |

Each person's next tasks: `docs/tasks/next/<name>.md`.
