# Agent Contracts - Pydantic schemas for all 5 data objects

> Source of truth: `docs/ARCHITECTURE.md` section 9 - Data Contracts.
> Python 3.10+ | Pydantic v2

```python
"""
DevForge - Agent Contracts
Pydantic v2 schemas for the 5 data objects defined in ARCHITECTURE.md section 9.
Python >= 3.10  |  Pydantic >= 2.0
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 1. ProjectContext
# ---------------------------------------------------------------------------

class ProjectContext(BaseModel):
    """The single shared record of a project's current state.

    The orchestrator is the only component that writes ``status``.

    Example::

        {
          "project_id": "proj_abc123",
          "idea": "A task-management SaaS for small teams",
          "status": "TESTING",
          "current_milestone_index": 1,
          "milestones": [],
          "retries": {"plan": 0, "test": 1, "security": 0},
          "human_approved_arch": false,
          "human_approved_release": false,
          "created_at": "2025-07-15T08:00:00Z"
        }
    """

    project_id: str
    idea: str
    status: Literal[
        "IDLE",
        "PLANNING",
        "BUILDING",
        "TESTING",
        "DEBUGGING",
        "SECURITY_FIX",
        "SECURED",
        "AWAITING_APPROVAL",
        "RELEASED",
        "FAILED",
    ]
    current_milestone_index: int
    milestones: list
    retries: dict[str, int]
    human_approved_arch: bool
    human_approved_release: bool
    created_at: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "proj_abc123",
                "idea": "A task-management SaaS for small teams",
                "status": "TESTING",
                "current_milestone_index": 1,
                "milestones": [],
                "retries": {"plan": 0, "test": 1, "security": 0},
                "human_approved_arch": False,
                "human_approved_release": False,
                "created_at": "2025-07-15T08:00:00Z",
            }
        }
    }


# ---------------------------------------------------------------------------
# 2. AgentResult
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    """Universal wrapper returned by every agent.

    Example::

        {
          "agent": "tester_agent",
          "milestone_id": "ms_001",
          "status": "FAIL",
          "summary": "17/20 tests passed. 3 failures in DELETE /tasks/{id}",
          "payload": {},
          "duration_seconds": 38,
          "timestamp": "2025-07-15T10:30:00Z"
        }
    """

    agent: str
    milestone_id: str
    status: Literal["PASS", "FAIL", "ERROR"]
    summary: str
    payload: dict
    duration_seconds: float
    timestamp: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "agent": "tester_agent",
                "milestone_id": "ms_001",
                "status": "FAIL",
                "summary": "17/20 tests passed. 3 failures in DELETE /tasks/{id}",
                "payload": {},
                "duration_seconds": 38,
                "timestamp": "2025-07-15T10:30:00Z",
            }
        }
    }


# ---------------------------------------------------------------------------
# 3. TestResult
# ---------------------------------------------------------------------------

class TestResult(BaseModel):
    """A single test-case result produced by the Tester Agent.

    Example::

        {
          "id": "test_045",
          "name": "test_delete_task_not_owner",
          "status": "FAIL",
          "error": "AssertionError: expected 403, got 200",
          "file": "backend/routers/tasks.py",
          "line": 54,
          "is_critical_path": true
        }
    """

    id: str
    name: str
    status: Literal["PASS", "FAIL"]
    error: Optional[str] = None
    file: str
    line: int
    is_critical_path: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "test_045",
                "name": "test_delete_task_not_owner",
                "status": "FAIL",
                "error": "AssertionError: expected 403, got 200",
                "file": "backend/routers/tasks.py",
                "line": 54,
                "is_critical_path": True,
            }
        }
    }


# ---------------------------------------------------------------------------
# 4. SecurityFinding
# ---------------------------------------------------------------------------

class SecurityFinding(BaseModel):
    """One finding from the Security Agent scan.

    Example::

        {
          "id": "SEC-012",
          "severity": "HIGH",
          "category": "broken_access_control",
          "description": "DELETE /tasks/{id} does not verify task ownership",
          "file": "backend/routers/tasks.py",
          "line": 54,
          "cwe": "CWE-639",
          "status": "OPEN"
        }
    """

    id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    category: str
    description: str
    file: str
    line: int
    cwe: str
    status: Literal["OPEN", "FIXED"]

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "SEC-012",
                "severity": "HIGH",
                "category": "broken_access_control",
                "description": "DELETE /tasks/{id} does not verify task ownership",
                "file": "backend/routers/tasks.py",
                "line": 54,
                "cwe": "CWE-639",
                "status": "OPEN",
            }
        }
    }


# ---------------------------------------------------------------------------
# 5. Decision
# ---------------------------------------------------------------------------

class Decision(BaseModel):
    """An architectural or technical choice recorded during the pipeline.

    Example::

        {
          "id": "DEC-007",
          "question": "Which database?",
          "alternatives": ["PostgreSQL", "MongoDB"],
          "decision": "PostgreSQL",
          "reason": "Relational data, ACID transactions required",
          "source": "plan_agent",
          "timestamp": "2025-07-15T09:14:00Z"
        }
    """

    id: str
    question: str
    alternatives: list[str]
    decision: str
    reason: str
    source: str
    timestamp: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "DEC-007",
                "question": "Which database?",
                "alternatives": ["PostgreSQL", "MongoDB"],
                "decision": "PostgreSQL",
                "reason": "Relational data, ACID transactions required",
                "source": "plan_agent",
                "timestamp": "2025-07-15T09:14:00Z",
            }
        }
    }
```