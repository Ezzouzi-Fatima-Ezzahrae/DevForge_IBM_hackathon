"""
tests/test_contracts.py
Validates the canonical JSON examples from docs/agent_contracts.md
against the Pydantic models in orchestrator/contracts.py.
"""

import pytest
from pydantic import ValidationError

from orchestrator.contracts import (
    AgentResult,
    Decision,
    GateResult,
    Milestone,
    ProjectContext,
    Requirement,
    SecurityFinding,
    TestResultData,
    validate_agent_result,
    validate_decision,
    validate_gate_result,
    validate_milestone,
    validate_project_context,
    validate_requirement,
    validate_security_finding,
    validate_test_result,
)


# ─── Canonical examples (copied from docs/agent_contracts.md) ─────────────────

PROJECT_CONTEXT_EXAMPLE = {
    "project_id": "proj_abc123",
    "idea": "Build a simple task-management SaaS for small teams",
    "status": "TESTING",
    "current_milestone_index": 0,
    "milestones": [],
    "retries": {"plan": 0, "test": 1, "security": 0},
    "human_approved_arch": True,
    "human_approved_release": False,
    "created_at": "2025-07-15T08:00:00Z",
}

REQUIREMENT_EXAMPLE = {
    "id": "REQ-003",
    "type": "functional",
    "user_story": "As a user, I can create a task with a title and due date",
    "acceptance_criteria": [
        "Task appears in my task list after creation",
        "Due date is stored and displayed correctly",
    ],
    "priority": "must_have",
}

MILESTONE_EXAMPLE = {
    "id": "ms_001",
    "title": "Task CRUD API",
    "description": "POST /tasks, GET /tasks, PATCH /tasks/{id}, DELETE /tasks/{id} with ownership checks",
    "order": 1,
    "requirement_ids": ["REQ-003", "REQ-004"],
    "status": "testing",
    "depends_on": [],
}

AGENT_RESULT_EXAMPLE = {
    "agent": "tester_agent",
    "status": "FAIL",
    "summary": "17/20 tests passed. 3 failures on DELETE /tasks/{id}.",
    "data": {
        "total": 20,
        "passed": 17,
        "failed": 1,
        "status": "FAIL",
        "failures": [
            {"test": "test_delete_task_not_owner", "error": "AssertionError: expected 403, got 200"}
        ],
        "coverage_percent": 72.0,
    },
    "duration_seconds": 38.1,
    "timestamp": "2025-07-15T10:30:00Z",
}

TEST_RESULT_PASS_EXAMPLE = {
    "total": 20,
    "passed": 20,
    "failed": 0,
    "status": "PASS",
    "failures": [],
    "coverage_percent": 85.0,
}

TEST_RESULT_FAIL_EXAMPLE = {
    "total": 20,
    "passed": 17,
    "failed": 3,
    "status": "FAIL",
    "failures": [
        {"test": "test_delete_task_not_owner", "error": "AssertionError: expected 403, got 200"},
        {"test": "test_delete_task_other_user", "error": "AssertionError: expected 403, got 200"},
        {"test": "test_delete_task_unauthenticated", "error": "AssertionError: expected 401, got 200"},
    ],
    "coverage_percent": 72.0,
}

SECURITY_FINDING_EXAMPLE = {
    "id": "SEC-001",
    "severity": "high",
    "type": "broken_access_control",
    "location": "backend/routers/tasks.py:54",
    "description": "DELETE /tasks/{id} does not verify that the requesting user owns the task",
    "recommended_fix": "Add: if task.owner_id != current_user.id: raise HTTPException(status_code=403)",
}

DECISION_EXAMPLE = {
    "id": "DEC-001",
    "project_id": "proj_abc123",
    "question": "Which database should we use?",
    "alternatives": ["PostgreSQL", "MongoDB", "SQLite"],
    "decision": "PostgreSQL",
    "reason": "Relational data with ACID transactions required; team already knows it",
    "source": "plan_agent",
    "timestamp": "2025-07-15T09:14:00Z",
}

GATE_RESULT_EXAMPLE = {
    "gate": "security",
    "project_id": "proj_abc123",
    "milestone_id": "ms_001",
    "verdict": "BLOCKED",
    "reason": "1 HIGH finding: broken_access_control at backend/routers/tasks.py:54",
    "retry_number": 0,
    "timestamp": "2025-07-15T10:50:00Z",
}


# ─── Tests: canonical examples parse without error ─────────────────────────────

def test_project_context_valid():
    ctx = validate_project_context(PROJECT_CONTEXT_EXAMPLE)
    assert ctx.project_id == "proj_abc123"
    assert ctx.status.value == "TESTING"
    assert ctx.retries["test"] == 1
    assert ctx.human_approved_arch is True


def test_requirement_valid():
    req = validate_requirement(REQUIREMENT_EXAMPLE)
    assert req.id == "REQ-003"
    assert req.type.value == "functional"
    assert len(req.acceptance_criteria) == 2
    assert req.priority.value == "must_have"


def test_milestone_valid():
    ms = validate_milestone(MILESTONE_EXAMPLE)
    assert ms.id == "ms_001"
    assert ms.order == 1
    assert ms.status.value == "testing"
    assert "REQ-003" in ms.requirement_ids


def test_agent_result_valid():
    result = validate_agent_result(AGENT_RESULT_EXAMPLE)
    assert result.agent == "tester_agent"
    assert result.status.value == "FAIL"
    assert result.data["passed"] == 17
    assert result.data["total"] == 20
    assert len(result.data["failures"]) == 1  # example has 1 failure entry


def test_test_result_pass_valid():
    tr = validate_test_result(TEST_RESULT_PASS_EXAMPLE)
    assert tr.passed == tr.total
    assert tr.failed == 0
    assert tr.status.value == "PASS"
    assert tr.coverage_percent == 85.0


def test_test_result_fail_valid():
    """Matches the exact fixture Manar will produce: 17/20, 3 failures."""
    tr = validate_test_result(TEST_RESULT_FAIL_EXAMPLE)
    assert tr.total == 20
    assert tr.passed == 17
    assert tr.failed == 3
    assert tr.status.value == "FAIL"
    assert len(tr.failures) == 3
    assert tr.failures[0].test == "test_delete_task_not_owner"
    assert tr.coverage_percent == 72.0


def test_security_finding_valid():
    finding = validate_security_finding(SECURITY_FINDING_EXAMPLE)
    assert finding.id == "SEC-001"
    assert finding.severity.value == "high"
    assert finding.type.value == "broken_access_control"
    assert "tasks.py:54" in finding.location


def test_decision_valid():
    dec = validate_decision(DECISION_EXAMPLE)
    assert dec.id == "DEC-001"
    assert dec.decision == "PostgreSQL"
    assert len(dec.alternatives) == 3
    assert dec.source == "plan_agent"


def test_gate_result_valid():
    gr = validate_gate_result(GATE_RESULT_EXAMPLE)
    assert gr.gate.value == "security"
    assert gr.verdict.value == "BLOCKED"
    assert gr.milestone_id == "ms_001"
    assert gr.retry_number == 0


# ─── Tests: gate_result with null milestone_id (plan gate) ────────────────────

def test_gate_result_null_milestone():
    plan_gate = {
        "gate": "plan",
        "project_id": "proj_abc123",
        "milestone_id": None,
        "verdict": "PASS",
        "reason": "6 user stories, 1 ADR, stack named",
        "retry_number": 0,
        "timestamp": "2025-07-15T08:30:00Z",
    }
    gr = validate_gate_result(plan_gate)
    assert gr.milestone_id is None
    assert gr.verdict.value == "PASS"


# ─── Tests: invalid values raise ValidationError ──────────────────────────────

def test_agent_result_invalid_status():
    bad = {**AGENT_RESULT_EXAMPLE, "status": "UNKNOWN"}
    with pytest.raises(ValidationError):
        validate_agent_result(bad)


def test_security_finding_invalid_severity():
    bad = {**SECURITY_FINDING_EXAMPLE, "severity": "extreme"}
    with pytest.raises(ValidationError):
        validate_security_finding(bad)


def test_gate_result_invalid_verdict():
    bad = {**GATE_RESULT_EXAMPLE, "verdict": "SKIPPED"}
    with pytest.raises(ValidationError):
        validate_gate_result(bad)


def test_gate_result_invalid_gate_name():
    bad = {**GATE_RESULT_EXAMPLE, "gate": "performance"}
    with pytest.raises(ValidationError):
        validate_gate_result(bad)


def test_requirement_empty_acceptance_criteria():
    bad = {**REQUIREMENT_EXAMPLE, "acceptance_criteria": []}
    with pytest.raises(ValidationError):
        validate_requirement(bad)


def test_milestone_invalid_status():
    bad = {**MILESTONE_EXAMPLE, "status": "in_progress"}
    with pytest.raises(ValidationError):
        validate_milestone(bad)


def test_project_context_invalid_status():
    bad = {**PROJECT_CONTEXT_EXAMPLE, "status": "RUNNING"}
    with pytest.raises(ValidationError):
        validate_project_context(bad)


# ─── Tests: Haytam security agent result shape ────────────────────────────────

def test_security_agent_result_blocked():
    """Full AgentResult as Haytam's security agent would return it."""
    result = validate_agent_result({
        "agent": "security_agent",
        "status": "FAIL",
        "summary": "1 HIGH finding. Pipeline BLOCKED.",
        "data": {
            "verdict": "BLOCKED",
            "counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            "findings": [SECURITY_FINDING_EXAMPLE],
        },
        "duration_seconds": 5.2,
        "timestamp": "2025-07-15T10:50:00Z",
    })
    assert result.status.value == "FAIL"
    assert result.data["verdict"] == "BLOCKED"
    assert result.data["counts"]["high"] == 1


def test_security_agent_result_pass():
    result = validate_agent_result({
        "agent": "security_agent",
        "status": "PASS",
        "summary": "No findings. Pipeline clear.",
        "data": {
            "verdict": "PASS",
            "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "findings": [],
        },
        "duration_seconds": 4.8,
        "timestamp": "2025-07-15T11:00:00Z",
    })
    assert result.status.value == "PASS"
    assert result.data["verdict"] == "PASS"


# ─── Tests: Manar debug agent result shape ────────────────────────────────────

def test_debug_agent_result():
    result = validate_agent_result({
        "agent": "debug_agent",
        "status": "PASS",
        "summary": "Fixed ownership check. All 20 tests pass.",
        "data": {
            "root_cause": "DELETE /tasks/{id} does not verify task ownership",
            "fix_applied": "Added ownership check",
            "fixed_file": "backend/routers/tasks.py",
            "rerun_result": {"total": 20, "passed": 20, "failed": 0, "status": "PASS"},
        },
        "duration_seconds": 14.3,
        "timestamp": "2025-07-15T10:45:00Z",
    })
    assert result.status.value == "PASS"
    assert result.data["rerun_result"]["passed"] == 20
