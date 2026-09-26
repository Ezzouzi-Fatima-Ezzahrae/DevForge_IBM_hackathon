# Safa: next tasks

**Branch:** `safae/memory`. **Folder:** `memory/`, plus tests in `tests/`.

## Status (reviewed)
Merged: decisions, gate results, metrics, `log_ingest.py`, `demo_test.py`, a detailed Bob session with screenshots. The memory demo runs. Your later fixes ("filter log_ingest by project_id") are on your branch, but **the merged code on `main` still uses the first event's project id and counts every event**, so the fix is not in `main` yet.

## Tasks (in order)

1. **Pull Request** from `safae/memory` into `main` with the log_ingest fix. Then check: run the pipeline twice, run ingest, and the numbers must not double.
2. **Aware datetimes:** replace `datetime.utcnow()` with timezone-aware times.
3. **Align with the contracts.** `memory/schemas.py` must accept exactly what the contracts define: `Decision.alternatives` needs at least one item, and `gate` names must be `plan`, `architecture`, `tests`, `security`, `release`. Import the models from `orchestrator/contracts.py` if possible.
4. **Tests** in `tests/test_memory.py` and `tests/test_metrics.py`: store and query a decision, filter by topic, gate results, metric summary, and the double-ingest check.
5. ~~Count only real approvals~~ **Done by the Leader:** live recording counts a human intervention only when the approval is not automatic.
6. ~~Structured data~~ **Done by the Leader:** the orchestrator now calls your `metrics.record_event`, `memory_agent.store` and `store_gate_result` directly (`orchestrator/recorder.py`). `log_ingest.py` is only a fallback; never run it for a project that was recorded live (double counting).
6b. **Decide how to show the test numbers.** Metrics are recorded per test run, so a run with 17/20 then 20/20 gives `tests_passed` 37 and `tests_failed` 3 (a sum of runs). For the slide, decide what is clearest (for example: first run 17/20, final 20/20, 3 bugs found and fixed) and compute it from `memory/data/metrics.json` (events are in time order). Only use real numbers.
7. **Functions for Ali**, documented at the top of the files: `query(project_id)`, `query_gate_results(project_id)`, `metrics.get_summary(project_id)`, `get_impact_summary(project_id)`.
8. **Context injection:** `get_context(project_id)` returns the top 5 decisions as a prompt prefix, with a test.
9. **Impact numbers:** the wiring is in. Delete `logs/orchestrator.jsonl`, do 3 clean runs, and give the Leader the real numbers (time per stage, tests before and after, retries, vulnerabilities found and fixed). A "before" baseline only from something you measured yourself.

## Done when
The Impact summary is correct after a fresh run, tests pass, and the plan agent's decisions appear in the decision log with the right project id.

## Talk to
Fati (decision format), Ali (which functions the API calls), Leader (log events).

## Demo role
Safa speaks about memory and the Impact numbers (about 30 seconds), using only real numbers from real runs. See `docs/DEMO_PLAN.md`. Feature freeze is at hour 40; after that only fix bugs that break a rehearsal.
