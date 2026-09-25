# Safa — Memory and Evaluation Lead

## Role
Memory and evaluation lead. Make DevForge remember and prove its value.

## Branch and Folder
- **Branch:** `safa/memory`
- **Folder:** `memory/`

---

## Objective
Build the Decision Memory module and the metrics system. Everything DevForge decides and measures must be stored, queryable, and displayable — so that judges can see real evidence of AI-driven development.

---

## Context
DevForge orchestrates: **Idea → Research → Requirements → Architecture → Milestones → Build → Test → Debug → Security → Human Approval → Release**.
Your module runs alongside every stage. It stores decisions made by agents, records how long each stage took, counts bugs found and fixed, vulnerabilities detected and patched, and human interventions required.
Demo app: a simple task-management SaaS. Stack: Python 3.11, PostgreSQL, FastAPI. Do not expand the stack.

Every agent returns:
```json
{ "agent": "...", "status": "PASS | FAIL | ERROR", "summary": "...", "data": {}, "duration_seconds": 0, "timestamp": "..." }
```

---

## Deliverables

- [ ] **Decision Memory** (`memory/memory_agent.py`)
  - `store(decision: dict) -> str` — persists a decision, returns its id.
  - `query(project_id: str, topic: str = None) -> list[dict]` — retrieves decisions, filtered by topic if provided.
  - `get_context(project_id: str) -> str` — returns a formatted string of all decisions for the given project, suitable for injecting into an agent prompt.
  - Decision schema:
    ```json
    {
      "id": "DEC-001",
      "project_id": "...",
      "question": "Which database should we use?",
      "alternatives": ["PostgreSQL", "MongoDB", "SQLite"],
      "decision": "PostgreSQL",
      "reason": "Relational data with ACID transactions required",
      "source": "architecture_agent",
      "timestamp": "2025-07-15T09:00:00Z"
    }
    ```

- [ ] **Metrics** (`memory/metrics.py`)
  - Records and exposes these counters per project:
    - `planning_time_seconds` — time from idea to first build
    - `implementation_time_seconds` — total build time across milestones
    - `testing_time_seconds` — total testing time
    - `debugging_time_seconds` — total debugging time
    - `security_findings_count` — total findings by severity
    - `tests_passed`, `tests_failed` — cumulative across all milestones
    - `retry_count` — how many times an agent was retried
    - `human_interventions` — how many times a human had to step in
  - Functions: `record_event(project_id, event_type, value)` and `get_summary(project_id) -> dict`.
  - **Use only real measured numbers. Never invent values.**

- [ ] **"DevForge Impact" summary** — a function that returns a human-readable comparison for the demo:
  - Time saved vs manual estimate
  - Bugs caught automatically
  - Vulnerabilities found and auto-patched
  - Human decisions required (should be very few)

- [ ] **Bob evidence:** `bob_sessions/safa_task01_memory.png` and `bob_sessions/safa_task02_metrics.png`.

---

## Dependencies

| Depends on | What you need |
|---|---|
| **Fati** | Research and architecture decisions must be stored via `memory_agent.store()` — coordinate the Decision schema before hour 4 |
| **Leader** | Orchestrator will call `memory_agent.store()` after each gate result; confirm the event types |
| **Ali** | `GET /decisions` and a future `GET /metrics` endpoint must match your data shapes |

---

## Bob Task
Use **Bob Agent mode** to design and build the memory and metrics module.
1. Run the prompt below for the memory module.
2. Screenshot → `bob_sessions/safa_task01_memory.png`.
3. Run a second session for the metrics module.
4. Screenshot → `bob_sessions/safa_task02_metrics.png`.

---

## Definition of Done
- [ ] `memory_agent.store(decision)` saves a decision and `memory_agent.query(project_id)` retrieves it.
- [ ] `metrics.record_event(...)` records an event and `metrics.get_summary(...)` returns correct counts.
- [ ] Both functions are testable via a short Python script (no API needed at this stage).
- [ ] Bonus: exposed via `GET /decisions?project_id=` in Ali's backend.
- [ ] Both Bob session screenshots saved in `bob_sessions/`.

---

## Deadline — First Sync (~hour 4)
Have `store()` and `query()` working with at least a JSON file backend (PostgreSQL can be wired in later). Confirm the Decision schema with Fati and confirm the metrics event types with the Leader.

---

## Bob Prompt

```
You are an expert Python engineer specialising in data persistence and metrics collection.

CONTEXT
Project: DevForge — an AI Software Development Lifecycle Orchestrator.
You are building the Decision Memory module and the Metrics module for DevForge.
Backend: FastAPI + PostgreSQL. Python 3.11. Do not add other tools.

TASK
1. Create memory/memory_agent.py with:
   - store(decision: dict) -> str
     Saves the decision to a JSON file at memory/data/decisions.json (append mode).
     Returns the decision id.
   - query(project_id: str, topic: str = None) -> list[dict]
     Reads memory/data/decisions.json, filters by project_id and optionally by topic
     (simple substring match on question + reason fields). Returns matching decisions.
   - get_context(project_id: str) -> str
     Returns a formatted string of all decisions for the project, one per line:
     "[DEC-001] <question> → <decision> (reason: <reason>)"

   Decision schema each dict must match:
   { "id": "DEC-NNN", "project_id": "...", "question": "...",
     "alternatives": ["..."], "decision": "...", "reason": "...",
     "source": "...", "timestamp": "..." }

2. Create memory/metrics.py with:
   - record_event(project_id: str, event_type: str, value: float | int) -> None
     Appends an event to memory/data/metrics.json.
     event_type is one of: planning_time, implementation_time, testing_time,
     debugging_time, security_finding, test_passed, test_failed, retry, human_intervention.
   - get_summary(project_id: str) -> dict
     Reads memory/data/metrics.json, aggregates counters for the project, returns:
     { "planning_time_seconds": 0, "implementation_time_seconds": 0,
       "testing_time_seconds": 0, "debugging_time_seconds": 0,
       "security_findings_count": 0, "tests_passed": 0, "tests_failed": 0,
       "retry_count": 0, "human_interventions": 0 }
   - get_impact_summary(project_id: str) -> str
     Returns a formatted human-readable summary string for the demo.

3. Create memory/data/.gitkeep so the directory is tracked by Git.

4. Create memory/schemas.py with Pydantic models for Decision and MetricEvent.

5. Create a short test script memory/demo_test.py that:
   - Stores 2 decisions
   - Queries them back
   - Records 3 metric events
   - Prints get_summary() and get_context()

CONSTRAINTS
- Use plain JSON files (memory/data/*.json) for storage now; PostgreSQL can be added later.
- Use uuid.uuid4() for decision IDs formatted as "DEC-{4-digit-number}" using a counter.
- Use datetime.utcnow().isoformat() + "Z" for timestamps.
- All files must be importable as: from memory.memory_agent import store, query

OUTPUT FORMAT
File tree first, then each file in full.
```
