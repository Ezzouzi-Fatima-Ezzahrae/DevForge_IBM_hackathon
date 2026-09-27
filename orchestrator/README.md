# Orchestrator

The DevForge orchestrator drives the pipeline with a state machine, quality gates and pluggable agents.
Every stage has a real agent, except build and fix which are stubs. Any real agent can be switched to its stub with an environment variable (`DEVFORGE_PLAN_AGENT_MODE=stub`, and the same for `TEST`, `DEBUG`, `SECURITY`).

## Run

```bash
pip install -r requirements.txt
python scripts/demo.py                                                   # narrated demo (restores the planted bug itself)
python -m orchestrator.run --idea "task management SaaS"                 # asks for human approval (y/n)
python -m orchestrator.run --idea "task management SaaS" --auto-approve  # no prompts
python -m orchestrator.run --idea "task management SaaS" --no-demo       # stubs always pass
python -m pytest -q                                                      # run the tests
python tests/restore_demo_bug.py                                         # after a manual run: put the planted bug back
```

Demo mode (default) shows the full story: tests fail (17/20) -> Debug -> 20/20, security BLOCKED -> Fix -> PASS, then human approval and RELEASE.

## Outputs

| File | Content | Read by |
|---|---|---|
| `logs/orchestrator.jsonl` | One JSON line per transition, agent call, gate, retry, approval | Safa (metrics), the API (events list) |
| `data/project_state.json` | Current `ProjectContext` (status, milestones, retries) | the API and the dashboard |
| `config/orchestrator_config.json` | Gate rules and retry limits | Leader |

## Flow

```
IDLE -> PLANNING -> (human approves architecture) -> BUILDING -> TESTING
TESTING: tests and security run in parallel
  tests FAIL         -> DEBUGGING -> (if security also blocked: SECURITY_FIX) -> TESTING
  tests PASS, security BLOCKED -> SECURITY_FIX -> TESTING
  both PASS          -> SECURED -> AWAITING_APPROVAL -> RELEASED
Retries (config/orchestrator_config.json): plan 2, test/debug 3, security fix 2. After that: FAILED (escalate to a human).
```

## Replace a stub with a real agent

Every agent implements `BaseAgent.run(context: ProjectContext) -> AgentResult` (see `agents_base.py`, `contracts.py`, `docs/agent_contracts.md`).

```python
from orchestrator import agents_base
agents_base.register_agent("test", MyRealTestingAgent())
```

| Stage name | Stub | Owner |
|---|---|---|
| `plan` | `agents/plan_agent.py` (stub: `stubs/plan_stub.py`) | Fati |
| `build` | `stubs/builder_stub.py` (stub only) | Leader |
| `test` | `agents/testing_agent` (stub: `stubs/tester_stub.py`) | Manar |
| `debug` | `agents/debug_agent` (stub: `stubs/debug_stub.py`) | Manar |
| `security` | `adapters/security_adapter.py` over `security/` (stub: `stubs/security_stub.py`) | Haytam |
| `fix` | `stubs/fix_stub.py` (stub only for now) | Haytam |

Decisions from the plan stage (ADRs) and the metrics are stored by `recorder.py`. The API reads `data/project_state.json` and `logs/orchestrator.jsonl`.

## Files

`state_machine.py` (allowed transitions), `runner.py` (pipeline loop, retries, parallel checks), `gates.py` (PASS/FAIL rules), `approval.py` (terminal approval), `approval_broker.py` (approval from the API), `logger.py` (JSON logging), `agents_base.py` (interface and registry), `contracts.py` (shared models), `run.py` (CLI), `stubs/` (fake agents).

## Approval from the API

By default the pipeline asks for the two human approvals (architecture, release) in the terminal. `run_pipeline` takes an optional `approval_fn` that replaces the terminal prompt; the API passes one built on `orchestrator/approval_broker.py`.

```python
from orchestrator.approval_broker import broker, make_approval_fn
from orchestrator.runner import run_pipeline

run_pipeline(idea, project_id=pid, approval_fn=make_approval_fn(pid))   # blocks at each approval
broker.pending(pid)         # None, or {"gate": "architecture"|"release", "gate_results": [...], "prompt": ...}
broker.resolve(pid, True)   # approve (False = reject); returns False if nothing was waiting
```

A timeout (default 10 minutes), a cancel or an error counts as a **rejection**, never as an approval. Rejecting the architecture ends in `FAILED`; rejecting the release returns to `BUILDING`.

The FastAPI backend (`backend/`) exposes this to the dashboard. Endpoints and response shapes: [`docs/API.md`](../docs/API.md).

```bash
uvicorn backend.main:app --port 8000          # run from the repository root
curl -X POST localhost:8000/projects -H "content-type: application/json" -d '{"idea":"task management SaaS"}'
curl -X POST localhost:8000/projects/<id>/start
curl localhost:8000/projects/<id>/status                       # stages, retries, awaiting_approval
curl -X POST localhost:8000/projects/<id>/approve -H "content-type: application/json" -d '{"gate":"architecture","approved":true}'
```

Each start restores the planted bug in `backend/demo_bug.py` first, so every run tells the same story.

## Memory and metrics (live recording)

`orchestrator/recorder.py` records what happens during a run, as it happens, in `memory/`:

| What | Where | When |
|---|---|---|
| Time per stage (planning, implementation, testing, debugging) | `metrics.record_event` | after each agent run |
| Tests passed and failed, per test run | `metrics.record_event` | after each test run |
| Security findings | `metrics.record_event` | after each security run that has findings |
| Retries | `metrics.record_event` | at each retry |
| Human interventions | `metrics.record_event` | only for real (non-automatic) approvals; `--auto-approve` does not count |
| Decisions from the plan agent | `memory_agent.store` | when the plan gate passes (always with the running project's id) |
| Every gate result | `memory_agent.store_gate_result` | after each gate |

Rules:
- A problem in memory or metrics is logged and the pipeline continues.
- Switch it off with `DEVFORGE_MEMORY=off` or `"memory": {"enabled": false}` in `config/orchestrator_config.json`.
- Live events are tagged with the run id `live-<project_id>`. Do **not** run `memory/log_ingest.py` for the same project, or the numbers are counted twice. `log_ingest.py` remains a fallback for runs recorded without live recording.
- Read the numbers with `memory.metrics.get_impact_summary(project_id)`.
- The `HUMAN_APPROVAL` log event now has an `auto` field (true when approved automatically).

Tests (`python -m pytest -q`) switch recording off by default (`tests/conftest.py`) and restore `backend/demo_bug.py` when the test session ends.
