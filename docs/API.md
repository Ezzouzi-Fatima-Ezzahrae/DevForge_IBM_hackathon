# Dashboard API (contract)

Everyone builds against this contract, so the backend and the screens can be written in parallel.
All responses are JSON. Base URL in development: `http://localhost:8000`. CORS is enabled.
Real data only: it comes from `data/project_state.json`, `logs/orchestrator.jsonl` and `memory/`.

## Projects

| Method and path | Body | Response |
|---|---|---|
| `POST /projects` | `{"idea": "task management SaaS"}` | `{"project_id": "proj_ab12cd34"}` |
| `POST /projects/{id}/start` | none | `{"status": "started"}` (the pipeline runs in the background; a run can only start once per project) |
| `GET /projects/{id}/status` | | see below |
| `POST /projects/{id}/approve` | `{"gate": "architecture" or "release", "approved": true or false}` | `{"status": "ok"}` |
| `POST /projects/{id}/reset` | none | restores `backend/demo_bug.py` (runs `tests/restore_demo_bug.py`) and returns `{"status": "ok"}` |

### `GET /projects/{id}/status`

```json
{
  "project_id": "proj_ab12cd34",
  "idea": "task management SaaS",
  "status": "TESTING",
  "retries": {"plan": 0, "test": 1, "security": 1},
  "running": true,
  "stages": [
    {"name": "plan",     "state": "done",    "verdict": "PASS",    "summary": "6 user stories, 3 ADR(s)", "duration_seconds": 0.0, "real": true},
    {"name": "build",    "state": "done",    "verdict": "PASS",    "summary": "...", "duration_seconds": 0.0, "real": false},
    {"name": "test",     "state": "failed",  "verdict": "FAIL",    "summary": "17/20 passed", "duration_seconds": 1.4, "real": true},
    {"name": "debug",    "state": "done",    "verdict": "PASS",    "summary": "Ownership fix applied", "duration_seconds": 1.2, "real": true},
    {"name": "security", "state": "pending", "verdict": null,      "summary": "", "duration_seconds": 0.0, "real": true},
    {"name": "fix",      "state": "pending", "verdict": null,      "summary": "", "duration_seconds": 0.0, "real": false},
    {"name": "approval", "state": "pending", "verdict": null,      "summary": "", "duration_seconds": 0.0, "real": true},
    {"name": "release",  "state": "pending", "verdict": null,      "summary": "", "duration_seconds": 0.0, "real": true}
  ],
  "awaiting_approval": null,
  "events": [
    {"ts": "2026-09-26T21:00:00+00:00", "event": "AGENT_DONE", "stage": "test", "msg": "17/20 tests passed"}
  ]
}
```

- `state` is one of `pending`, `running`, `done`, `failed`.
- `real` is `false` for stages that still use a stub (build, fix). The screen must show them as "stub" so nothing is misleading.
- `awaiting_approval` is `null`, or `{"gate": "architecture" or "release", "gate_results": [{"gate": "tests", "verdict": "PASS", "reason": "..."}]}` while the pipeline waits for a human.
- `status` can also be `FAILED` (retries used up): show a red "Needs human attention" banner.

## Insights (read-only)

| Path | Response |
|---|---|
| `GET /projects/{id}/decisions` | list of decisions from `memory_agent.query(project_id)` |
| `GET /projects/{id}/gates` | list of gate results from `memory_agent.query_gate_results(project_id)` |
| `GET /projects/{id}/metrics` | `{"summary": {...metrics.get_summary}, "impact_text": "..."}` |
| `GET /projects/{id}/tests` | test runs: `[{"attempt": 1, "passed": 17, "total": 20, "failures": ["test_a", "test_b"]}]` (from the log) |
| `GET /projects/{id}/security` | security runs: `[{"attempt": 1, "verdict": "BLOCKED", "findings": [{"severity": "high", "type": "...", "location": "backend/demo_bug.py:36"}]}]` (from the log) |

## Screens (three, plain HTML, no build step)

1. **Pipeline** (main demo screen): one card per stage with state colour, verdict, summary, duration, retry badges, the "stub" label, and a live event list. Polls `/status` every 2 seconds. Start button (creates the project and starts it) and Reset button.
2. **Approval**: appears when `awaiting_approval` is not null. Shows the gate results and two buttons, Approve and Request changes, calling `/approve`.
3. **Insights**: decision log table, gate results, test runs, security runs, and the Impact panel. Real numbers only, with the exact wording agreed with Safa.

Served by FastAPI at `/` from `frontend/static/` (`index.html`, `insights.html`, `style.css`, `pipeline.js`, `insights.js`).
