# Agent Contracts — Pydantic schemas for all data objects

This file is the **single source of truth** for all inter-component data contracts in DevForge.
Every agent boundary uses exactly one of these objects. No free-form data is passed between components.

---

## Python Models

```python
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# ProjectContext
# ---------------------------------------------------------------------------

class ProjectContext(BaseModel):
    project_id: str
    idea: str
    status: str = "IDLE"
    current_milestone_index: int = 0
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    retries: Dict[str, int] = Field(default_factory=lambda: {"plan": 0, "test": 0, "security": 0})
    human_approved_arch: bool = False
    human_approved_release: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    agent: str                          # e.g. "security_agent", "tester_agent"
    milestone_id: str
    status: str                         # "PASS" | "BLOCKED" | "FAIL" | "ERROR"
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# TestResult
# ---------------------------------------------------------------------------

class TestResult(BaseModel):
    id: str
    name: str
    status: str                         # "PASS" | "FAIL"
    error: Optional[str] = None
    file: str
    line: int
    is_critical_path: bool = False


# ---------------------------------------------------------------------------
# SecurityFinding
# ---------------------------------------------------------------------------

class SecurityFinding(BaseModel):
    id: str                             # e.g. "SEC-001"
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    category: str                       # e.g. "broken_access_control"
    description: str
    file: str                           # relative path, e.g. "backend/routers/tasks.py"
    line: int
    cwe: str                            # e.g. "CWE-639"
    status: Literal["OPEN", "FIXED"]
    evidence: Optional[str] = None      # code snippet or scan output excerpt
    recommendation: Optional[str] = None


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

class Decision(BaseModel):
    id: str                             # e.g. "DEC-007"
    question: str
    alternatives: List[str]
    decision: str
    reason: str
    source: str                         # agent name that produced this decision
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## JSON Examples

### AgentResult — Security BLOCKED

```json
{
  "agent": "security_agent",
  "milestone_id": "ms_001",
  "status": "BLOCKED",
  "summary": "1 HIGH finding: broken access control on DELETE /tasks/{id}",
  "payload": {
    "verdict": "BLOCKED",
    "findings": [
      {
        "id": "SEC-001",
        "severity": "HIGH",
        "category": "broken_access_control",
        "description": "DELETE /tasks/{id} does not verify task ownership before deletion",
        "file": "backend/routers/tasks.py",
        "line": 54,
        "cwe": "CWE-639",
        "status": "OPEN",
        "evidence": "task is deleted without checking task.owner_id == current_user.id",
        "recommendation": "Fetch the task first, verify task.owner_id == current_user.id, raise HTTP 403 if not."
      }
    ],
    "critical_count": 0,
    "high_count": 1,
    "medium_count": 0
  },
  "duration_seconds": 4.2,
  "timestamp": "2025-07-15T10:45:00Z"
}
```

### AgentResult — Security PASS (after fix)

```json
{
  "agent": "security_agent",
  "milestone_id": "ms_001",
  "status": "PASS",
  "summary": "0 critical, 0 high findings. Security gate PASS.",
  "payload": {
    "verdict": "PASS",
    "findings": [
      {
        "id": "SEC-001",
        "severity": "HIGH",
        "category": "broken_access_control",
        "description": "DELETE /tasks/{id} does not verify task ownership before deletion",
        "file": "backend/routers/tasks.py",
        "line": 54,
        "cwe": "CWE-639",
        "status": "FIXED",
        "evidence": "Ownership check added: task.owner_id == current_user.id",
        "recommendation": "Fetch the task first, verify task.owner_id == current_user.id, raise HTTP 403 if not."
      }
    ],
    "critical_count": 0,
    "high_count": 0,
    "medium_count": 0
  },
  "duration_seconds": 3.9,
  "timestamp": "2025-07-15T11:10:00Z"
}
```

### SecurityFinding

```json
{
  "id": "SEC-012",
  "severity": "HIGH",
  "category": "broken_access_control",
  "description": "DELETE /tasks/{id} does not verify task ownership",
  "file": "backend/routers/tasks.py",
  "line": 54,
  "cwe": "CWE-639",
  "status": "OPEN",
  "evidence": "No ownership check before delete_task(task_id)",
  "recommendation": "Add: if task.owner_id != current_user.id: raise HTTPException(403)"
}
```

### Decision

```json
{
  "id": "DEC-007",
  "question": "Which database?",
  "alternatives": ["PostgreSQL", "MongoDB"],
  "decision": "PostgreSQL",
  "reason": "Relational data, ACID transactions required",
  "source": "plan_agent",
  "timestamp": "2025-07-15T09:14:00Z"
}
```
