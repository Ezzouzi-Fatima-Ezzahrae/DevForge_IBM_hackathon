# Orchestrator

The DevForge orchestrator drives the pipeline with a state machine, quality gates and pluggable agents.
It runs today with **stub agents**, so each teammate can replace one stub with their real agent without touching the rest.

## Run

```bash
pip install pydantic pytest
python -m orchestrator.run --idea "task management SaaS"                 # asks for human approval (y/n)
python -m orchestrator.run --idea "task management SaaS" --auto-approve  # no prompts
python -m orchestrator.run --idea "task management SaaS" --no-demo       # stubs always pass
python -m pytest -q                                                      # run the tests
```

Demo mode (default) shows the full story: tests fail (17/20) -> Debug -> 20/20, security BLOCKED -> Fix -> PASS, then human approval and RELEASE.

## Outputs

| File | Content | Read by |
|---|---|---|
| `logs/orchestrator.jsonl` | One JSON line per transition, agent call, gate, retry, approval | Safa (metrics), Ali (activity view) |
| `data/project_state.json` | Current `ProjectContext` (status, milestones, retries) | Ali (backend and dashboard) |
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
| `plan` | `stubs/plan_stub.py` (research, requirements, architecture) | Fati |
| `build` | `stubs/builder_stub.py` | Ali / Leader |
| `test` | `stubs/tester_stub.py` | Manar |
| `debug` | `stubs/debug_stub.py` | Manar |
| `security` | `stubs/security_stub.py` | Haytam |
| `fix` | `stubs/fix_stub.py` | Haytam |

Safa reads `logs/orchestrator.jsonl` for metrics and stores decisions from the plan stage (ADRs). Ali reads `data/project_state.json`.

## Files

`state_machine.py` (allowed transitions), `runner.py` (pipeline loop, retries, parallel checks), `gates.py` (PASS/FAIL rules), `approval.py` (human approval), `logger.py` (JSON logging), `agents_base.py` (interface and registry), `contracts.py` (shared models), `run.py` (CLI), `stubs/` (fake agents).
