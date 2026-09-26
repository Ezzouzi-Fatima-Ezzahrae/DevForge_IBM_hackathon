# Safa: next tasks

**Branch:** `safae/memory`. **Folder:** `memory/`, plus tests in `tests/`.

## Status (reviewed)
Merged: decisions, gate results, metrics, `log_ingest.py`, `demo_test.py`, a detailed Bob session with screenshots. The memory demo runs. Your later fixes ("filter log_ingest by project_id") are on your branch, but **the merged code on `main` still uses the first event's project id and counts every event**, so the fix is not in `main` yet.

## Tasks (in order)

1. **Pull Request** from `safae/memory` into `main` with the log_ingest fix. Then check: run the pipeline twice, run ingest, and the numbers must not double.
2. **Aware datetimes:** replace `datetime.utcnow()` with timezone-aware times.
3. **Align with the contracts.** `memory/schemas.py` must accept exactly what the contracts define: `Decision.alternatives` needs at least one item, and `gate` names must be `plan`, `architecture`, `tests`, `security`, `release`. Import the models from `orchestrator/contracts.py` if possible.
4. **Tests** in `tests/test_memory.py` and `tests/test_metrics.py`: store and query a decision, filter by topic, gate results, metric summary, and the double-ingest check.
5. **Count only real approvals.** The Leader will add an `auto` field to the `HUMAN_APPROVAL` log event. Use it.
6. **Parse structured data, not text.** `log_ingest.py` reads numbers out of summaries ("17/20", "1 HIGH"). Ask the Leader to add structured fields to the log events, or read `data/project_state.json`, so a wording change cannot break the metrics.
7. **Functions for Ali**, documented at the top of the files: `query(project_id)`, `query_gate_results(project_id)`, `metrics.get_summary(project_id)`, `get_impact_summary(project_id)`.
8. **Context injection:** `get_context(project_id)` returns the top 5 decisions as a prompt prefix, with a test.
9. **Impact numbers:** once the pipeline is connected, delete `logs/orchestrator.jsonl`, do 3 clean runs, and give the Leader the real numbers (time per stage, tests before and after, retries, vulnerabilities found and fixed). A "before" baseline only from something you measured yourself.

## Done when
The Impact summary is correct after a fresh run, tests pass, and the plan agent's decisions appear in the decision log with the right project id.

## Talk to
Fati (decision format), Ali (which functions the API calls), Leader (log events).
