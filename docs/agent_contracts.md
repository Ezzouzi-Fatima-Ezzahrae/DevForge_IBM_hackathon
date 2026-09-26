# DevForge — Agent Contracts

> **Version 1.0 — published by the Leader at hour 3.**
> These are the canonical data shapes used by every agent and the orchestrator.
> Do not invent extra fields. If you need a new field, ask the Leader first.

---

## How to Use (quick guide per member)

### Fati — Plan Agent (Research + Requirements + Architecture)

Your agent must return an `AgentResult`. Put everything inside `data`.

```python
# agents/plan_agent.py
from datetime import datetime, timezone
import time

def run(idea: str) -> dict:
    start = time.time()
    # ... your logic ...
    return {
        "agent": "plan_agent",
        "status": "PASS",          # "PASS" | "FAIL" | "ERROR"
        "summary": "Generated 6 user stories and 1 ADR for task-management SaaS",
        "data": {
            "requirements": [...],     # list of Requirement dicts
            "architecture": {...},     # architecture doc dict
            "decisions": [...]         # list of Decision dicts
        },
        "duration_seconds": round(time.time() - start, 2),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

Gate check (Plan Gate): `len(data["requirements"]) >= 5` and `data["architecture"]["adr"]` is non-empty.

---

### Manar — Testing Agent and Debugger Agent

**Testing Agent** puts a `TestResult` inside `data`:

```python
return {
    "agent": "tester_agent",
    "status": "FAIL",             # outer AgentResult status
    "summary": "17/20 tests passed. 3 failures on DELETE /tasks/{id}",
    "data": {
        "total": 20, "passed": 17, "failed": 3,
        "status": "FAIL",         # inner gate decision — PASS only when passed == total
        "failures": [
            {"test": "test_delete_task_not_owner",
             "error": "AssertionError: expected 403, got 200"}
        ],
        "coverage_percent": 72.0
    },
    "duration_seconds": 38.1,
    "timestamp": "2025-07-15T10:30:00Z"
}
```

**Debugger Agent** puts a `DebugResult` inside `data`:

```python
return {
    "agent": "debug_agent",
    "status": "PASS",
    "summary": "Fixed ownership check on DELETE /tasks/{id}. All 20 tests pass.",
    "data": {
        "root_cause": "DELETE /tasks/{id} does not verify task ownership",
        "fix_applied": "Added: if task.owner_id != current_user.id: raise HTTPException(403)",
        "fixed_file": "backend/routers/tasks.py",
        "rerun_result": {"total": 20, "passed": 20, "failed": 0, "status": "PASS"}
    },
    "duration_seconds": 14.3,
    "timestamp": "2025-07-15T10:45:00Z"
}
```

Gate check (Test Gate): `data["passed"] == data["total"]`.

---

### Haytam — Security Agent

Return an `AgentResult` where `data` holds a list of `SecurityFinding` dicts and a verdict:

```python
return {
    "agent": "security_agent",
    "status": "FAIL",             # PASS or FAIL (use FAIL when verdict is BLOCKED)
    "summary": "1 HIGH finding. Pipeline BLOCKED.",
    "data": {
        "verdict": "BLOCKED",     # "PASS" | "BLOCKED"
        "counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
        "findings": [
            {
                "id": "SEC-001",
                "severity": "high",
                "type": "broken_access_control",
                "location": "backend/routers/tasks.py:54",
                "description": "DELETE /tasks/{id} does not verify task ownership",
                "recommended_fix": "Check task.owner_id == current_user.id before deleting"
            }
        ]
    },
    "duration_seconds": 5.2,
    "timestamp": "2025-07-15T10:50:00Z"
}
```

Gate check (Security Gate): `data["verdict"] == "PASS"` (i.e. counts.critical == 0 and counts.high == 0).

Agree this format with Manar — `PASS`/`FAIL` on `AgentResult.status`, `PASS`/`BLOCKED` on `data.verdict`.

---

### Safa — Memory Agent (Decision and Metrics)

**Storing a Decision** — call `memory_agent.store(decision_dict)` where the dict matches:

```python
decision = {
    "id": "DEC-001",                          # auto-generated is fine
    "project_id": "proj_abc123",
    "question": "Which database should we use?",
    "alternatives": ["PostgreSQL", "MongoDB", "SQLite"],
    "decision": "PostgreSQL",
    "reason": "Relational data with ACID transactions required",
    "source": "plan_agent",                   # which agent made this decision
    "timestamp": "2025-07-15T09:14:00Z"
}
```

**Recording a metric event** — call `metrics.record_event(project_id, event_type, value)`:

```python
metrics.record_event("proj_abc123", "test_passed", 20)
metrics.record_event("proj_abc123", "security_finding", 1)
metrics.record_event("proj_abc123", "retry", 1)
```

Allowed event types: `planning_time` | `implementation_time` | `testing_time` | `debugging_time` | `security_finding` | `test_passed` | `test_failed` | `retry` | `human_intervention`.

---

### Ali — Backend and Dashboard

**Reading AgentResult** from `GET /agents/results?project_id=`:

```python
# Every item in the response list is an AgentResult
result = {
    "agent": "tester_agent",
    "status": "PASS",
    "summary": "20/20 tests passed",
    "data": {...},              # agent-specific, see above
    "duration_seconds": 38.1,
    "timestamp": "2025-07-15T10:30:00Z"
}
```

**Reading GateResult** — the orchestrator writes one after each gate evaluation:

```python
gate_result = {
    "gate": "tests",            # "plan" | "architecture" | "tests" | "security" | "release"
    "project_id": "proj_abc123",
    "milestone_id": "ms_001",   # null for plan/architecture/release gates
    "verdict": "PASS",          # "PASS" | "FAIL" | "BLOCKED"
    "reason": "20/20 tests passed, coverage 80%",
    "retry_number": 0,
    "timestamp": "2025-07-15T10:31:00Z"
}
```

The pipeline page should poll `GET /projects/{id}/status` every 3 s. The response includes
`project.status` (the FSM state) plus the list of gate results — use those to render each stage badge.

---

## Object Definitions

---

### 1. ProjectContext

**Purpose:** The single shared record of a project's current state. The orchestrator owns it and is the only component that writes `status`.

**Produced by:** Orchestrator (on `POST /projects`)  
**Consumed by:** All agents (read-only), Backend API, Dashboard

| Field | Type | Allowed values / notes |
|---|---|---|
| `project_id` | `str` | UUID, e.g. `"proj_abc123"` |
| `idea` | `str` | Raw idea text from the user |
| `status` | `str` | `IDLE` \| `PLANNING` \| `BUILDING` \| `TESTING` \| `DEBUGGING` \| `SECURITY_FIX` \| `SECURED` \| `AWAITING_APPROVAL` \| `RELEASED` \| `ERROR` |
| `current_milestone_index` | `int` | 0-based index into `milestones` list |
| `milestones` | `list[Milestone]` | Ordered list; empty until planning completes |
| `retries` | `dict[str, int]` | Keys: `"plan"`, `"test"`, `"security"` |
| `human_approved_arch` | `bool` | Set to `true` after architecture sign-off |
| `human_approved_release` | `bool` | Set to `true` after release sign-off |
| `created_at` | `str` | ISO 8601 UTC timestamp |

```json
{
  "project_id": "proj_abc123",
  "idea": "Build a simple task-management SaaS for small teams",
  "status": "TESTING",
  "current_milestone_index": 0,
  "milestones": [],
  "retries": { "plan": 0, "test": 1, "security": 0 },
  "human_approved_arch": true,
  "human_approved_release": false,
  "created_at": "2025-07-15T08:00:00Z"
}
```

---

### 2. Requirement

**Purpose:** A single buildable user story with its acceptance criterion.

**Produced by:** Plan Agent  
**Consumed by:** Orchestrator (plan gate check), Architecture Agent, Milestone Planner, Dashboard

| Field | Type | Allowed values / notes |
|---|---|---|
| `id` | `str` | e.g. `"REQ-001"` |
| `type` | `str` | `"functional"` \| `"non_functional"` |
| `user_story` | `str` | "As a [role], I can [action]" |
| `acceptance_criteria` | `list[str]` | At least one item |
| `priority` | `str` | `"must_have"` \| `"should_have"` \| `"nice_to_have"` |

```json
{
  "id": "REQ-003",
  "type": "functional",
  "user_story": "As a user, I can create a task with a title and due date",
  "acceptance_criteria": [
    "Task appears in my task list after creation",
    "Due date is stored and displayed correctly"
  ],
  "priority": "must_have"
}
```

---

### 3. Milestone

**Purpose:** One buildable slice of work; the unit the Builder Agent operates on.

**Produced by:** Orchestrator (Milestone Planner, inlined)  
**Consumed by:** Builder Agent, Tester Agent, Security Agent, Dashboard

| Field | Type | Allowed values / notes |
|---|---|---|
| `id` | `str` | e.g. `"ms_001"` |
| `title` | `str` | Short description, e.g. `"Task CRUD API"` |
| `description` | `str` | What to build |
| `order` | `int` | 1-based execution order |
| `requirement_ids` | `list[str]` | REQ ids this milestone satisfies |
| `status` | `str` | `"pending"` \| `"building"` \| `"testing"` \| `"approved"` \| `"failed"` |
| `depends_on` | `list[str]` | Milestone ids that must be approved first |

```json
{
  "id": "ms_001",
  "title": "Task CRUD API",
  "description": "POST /tasks, GET /tasks, PATCH /tasks/{id}, DELETE /tasks/{id} with ownership checks",
  "order": 1,
  "requirement_ids": ["REQ-003", "REQ-004"],
  "status": "testing",
  "depends_on": []
}
```

---

### 4. AgentResult

**Purpose:** The universal wrapper every agent returns. The `data` field carries agent-specific content.

**Produced by:** Every agent  
**Consumed by:** Orchestrator (gate evaluation), Backend API (`POST /agents/results`), Dashboard

| Field | Type | Allowed values / notes |
|---|---|---|
| `agent` | `str` | Agent identifier, e.g. `"plan_agent"`, `"tester_agent"` |
| `status` | `str` | `"PASS"` \| `"FAIL"` \| `"ERROR"` |
| `summary` | `str` | One human-readable sentence |
| `data` | `dict` | Agent-specific payload (see per-agent examples above) |
| `duration_seconds` | `float` | Wall-clock seconds the agent ran |
| `timestamp` | `str` | ISO 8601 UTC, e.g. `"2025-07-15T10:30:00Z"` |

```json
{
  "agent": "tester_agent",
  "status": "FAIL",
  "summary": "17/20 tests passed. 3 failures on DELETE /tasks/{id}.",
  "data": {
    "total": 20,
    "passed": 17,
    "failed": 3,
    "failures": [
      { "test": "test_delete_task_not_owner", "error": "AssertionError: expected 403, got 200" }
    ],
    "coverage_percent": 72.0
  },
  "duration_seconds": 38.1,
  "timestamp": "2025-07-15T10:30:00Z"
}
```

---

### 5. TestResult

**Purpose:** The `data` payload of the Tester Agent's `AgentResult`. Also the shape returned by `GET /tests`.

**Produced by:** Tester Agent  
**Consumed by:** Orchestrator (test gate check), Debugger Agent, Dashboard

| Field | Type | Allowed values / notes |
|---|---|---|
| `total` | `int` | Total number of tests run |
| `passed` | `int` | Number that passed |
| `failed` | `int` | Number that failed |
| `status` | `str` | `"PASS"` \| `"FAIL"` — gate decision inline; `PASS` only when `passed == total` |
| `failures` | `list[dict]` | Each item: `{"test": str, "error": str}` |
| `coverage_percent` | `float` | 0–100 |

Gate rule (orchestrator re-checks): `PASS` only when `passed == total`.

```json
{
  "total": 20,
  "passed": 20,
  "failed": 0,
  "status": "PASS",
  "failures": [],
  "coverage_percent": 85.0
}
```

---

### 6. SecurityFinding

**Purpose:** One finding from the Security Agent scan. A list of these lives in `AgentResult.data.findings`.
Also the shape returned by `GET /security`.

**Produced by:** Security Agent  
**Consumed by:** Orchestrator (security gate check), Builder Agent (for fix input), Dashboard

| Field | Type | Allowed values / notes |
|---|---|---|
| `id` | `str` | e.g. `"SEC-001"` |
| `severity` | `str` | `"critical"` \| `"high"` \| `"medium"` \| `"low"` |
| `type` | `str` | `"broken_access_control"` \| `"injection"` \| `"secrets_exposure"` \| `"misconfiguration"` \| `"vulnerable_dependency"` \| `"xss"` \| `"csrf"` |
| `location` | `str` | `"file/path.py:line_number"` |
| `description` | `str` | What the problem is |
| `recommended_fix` | `str` | How to fix it |

Security gate verdict logic (inside `AgentResult.data`):
- `verdict = "PASS"` when `counts.critical == 0` and `counts.high == 0`
- `verdict = "BLOCKED"` otherwise

```json
{
  "id": "SEC-001",
  "severity": "high",
  "type": "broken_access_control",
  "location": "backend/routers/tasks.py:54",
  "description": "DELETE /tasks/{id} does not verify that the requesting user owns the task",
  "recommended_fix": "Add: if task.owner_id != current_user.id: raise HTTPException(status_code=403)"
}
```

---

### 7. Decision

**Purpose:** Records an architectural or technical choice made during the pipeline. Stored by the Memory Agent so future agents can retrieve context.

**Produced by:** Plan Agent, Architecture Agent (via `memory_agent.store()`)  
**Consumed by:** Memory Agent (storage), Orchestrator (reads context before invoking agents), Dashboard (`GET /decisions`)

| Field | Type | Allowed values / notes |
|---|---|---|
| `id` | `str` | e.g. `"DEC-001"` |
| `project_id` | `str` | Links to `ProjectContext.project_id` |
| `question` | `str` | The decision that had to be made |
| `alternatives` | `list[str]` | Options that were considered |
| `decision` | `str` | The chosen option |
| `reason` | `str` | Why this option was chosen |
| `source` | `str` | Agent or person that made the decision |
| `timestamp` | `str` | ISO 8601 UTC |

```json
{
  "id": "DEC-001",
  "project_id": "proj_abc123",
  "question": "Which database should we use?",
  "alternatives": ["PostgreSQL", "MongoDB", "SQLite"],
  "decision": "PostgreSQL",
  "reason": "Relational data with ACID transactions required; team already knows it",
  "source": "plan_agent",
  "timestamp": "2025-07-15T09:14:00Z"
}
```

---

### 8. GateResult

**Purpose:** The orchestrator writes one `GateResult` after evaluating each quality gate. The dashboard reads these to render stage badges.

**Produced by:** Orchestrator  
**Consumed by:** Memory Agent (stored), Backend API, Dashboard

| Field | Type | Allowed values / notes |
|---|---|---|
| `gate` | `str` | `"plan"` \| `"architecture"` \| `"tests"` \| `"security"` \| `"release"` |
| `project_id` | `str` | Links to `ProjectContext.project_id` |
| `milestone_id` | `str \| None` | `null` for plan / architecture / release gates |
| `verdict` | `str` | `"PASS"` \| `"FAIL"` \| `"BLOCKED"` |
| `reason` | `str` | One-line explanation |
| `retry_number` | `int` | 0 = first attempt |
| `timestamp` | `str` | ISO 8601 UTC |

```json
{
  "gate": "security",
  "project_id": "proj_abc123",
  "milestone_id": "ms_001",
  "verdict": "BLOCKED",
  "reason": "1 HIGH finding: broken_access_control at backend/routers/tasks.py:54",
  "retry_number": 0,
  "timestamp": "2025-07-15T10:50:00Z"
}
```

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0 | Day 1 H3 | Initial publication — 8 objects defined |
