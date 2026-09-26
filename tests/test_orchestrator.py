"""
tests/test_orchestrator.py
Unit + integration tests for the orchestrator.

Covers:
- Valid and invalid state transitions
- Retry limit and escalation
- Each gate's pass/fail rules
- Full end-to-end run with stubs (auto_approve + no-demo and demo mode)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from orchestrator.contracts import (
    AgentResult,
    AgentStatus,
    GateName,
    GateVerdict,
    ProjectContext,
    ProjectStatus,
)
from orchestrator.gates import (
    evaluate_plan_gate,
    evaluate_security_gate,
    evaluate_test_gate,
    evaluate_release_gate,
)
from orchestrator.state_machine import InvalidTransitionError, StateMachine, TRANSITIONS
from orchestrator.runner import run_pipeline
from orchestrator import agents_base


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx() -> ProjectContext:
    from datetime import datetime, timezone
    return ProjectContext(
        project_id="test_proj",
        idea="task management SaaS",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _agent_result(status: str = "PASS", data: dict | None = None) -> AgentResult:
    from datetime import datetime, timezone
    return AgentResult(
        agent="test_stub",
        status=AgentStatus(status),
        summary=f"stub result {status}",
        data=data or {},
        duration_seconds=0.01,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ─── State machine: valid transitions ─────────────────────────────────────────

def test_valid_transitions_forward():
    sm = StateMachine(ProjectStatus.IDLE)
    sm.advance(ProjectStatus.PLANNING)
    assert sm.state == ProjectStatus.PLANNING

    sm.advance(ProjectStatus.BUILDING)
    assert sm.state == ProjectStatus.BUILDING

    sm.advance(ProjectStatus.TESTING)
    assert sm.state == ProjectStatus.TESTING

    sm.advance(ProjectStatus.SECURED)
    assert sm.state == ProjectStatus.SECURED

    sm.advance(ProjectStatus.AWAITING_APPROVAL)
    assert sm.state == ProjectStatus.AWAITING_APPROVAL

    sm.advance(ProjectStatus.RELEASED)
    assert sm.state == ProjectStatus.RELEASED


def test_debug_loop_transitions():
    sm = StateMachine(ProjectStatus.TESTING)
    sm.advance(ProjectStatus.DEBUGGING)
    assert sm.state == ProjectStatus.DEBUGGING
    sm.advance(ProjectStatus.TESTING)
    assert sm.state == ProjectStatus.TESTING


def test_security_fix_loop_transitions():
    sm = StateMachine(ProjectStatus.SECURED)
    sm.advance(ProjectStatus.SECURITY_FIX)
    sm.advance(ProjectStatus.SECURED)
    assert sm.state == ProjectStatus.SECURED


def test_terminal_states_have_no_transitions():
    for terminal in (ProjectStatus.RELEASED, ProjectStatus.FAILED, ProjectStatus.ERROR):
        sm = StateMachine(terminal)
        assert sm.can_advance(ProjectStatus.PLANNING) is False


# ─── State machine: invalid transitions ───────────────────────────────────────

def test_invalid_transition_raises():
    sm = StateMachine(ProjectStatus.IDLE)
    with pytest.raises(InvalidTransitionError):
        sm.advance(ProjectStatus.RELEASED)


def test_cannot_go_from_released_to_planning():
    sm = StateMachine(ProjectStatus.RELEASED)
    with pytest.raises(InvalidTransitionError):
        sm.advance(ProjectStatus.PLANNING)


def test_cannot_skip_planning():
    sm = StateMachine(ProjectStatus.IDLE)
    with pytest.raises(InvalidTransitionError):
        sm.advance(ProjectStatus.BUILDING)


# ─── Retry limit and escalation ───────────────────────────────────────────────

def test_test_gate_fail_escalates_at_limit(ctx):
    """run_pipeline with a stub that always fails should hit FAILED after test_max retries."""
    from orchestrator.stubs.tester_stub import TesterStub
    from orchestrator.stubs.security_stub import SecurityStub

    # Stub that always fails
    class AlwaysFailTester(TesterStub):
        def __init__(self):
            super().__init__(fail_first=True)
            self._call_count = 0
        def run(self, context):
            self._call_count += 1
            from datetime import datetime, timezone
            return AgentResult(
                agent="tester_agent",
                status=AgentStatus.FAIL,
                summary="always fail",
                data={"total": 5, "passed": 3, "failed": 2, "status": "FAIL",
                      "failures": [{"test": "t1", "error": "e1"}],
                      "coverage_percent": 60.0},
                duration_seconds=0.01,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    agents_base.register_agent("test", AlwaysFailTester())
    agents_base.register_agent("security", SecurityStub(fail_first=False))

    result = run_pipeline(
        idea="test idea",
        project_id="esc_test",
        auto_approve=True,
        demo_mode=False,
    )
    assert result.status == ProjectStatus.FAILED

    # Restore stubs
    from orchestrator.stubs.tester_stub import TesterStub as TS
    agents_base.register_agent("test", TS())
    agents_base.register_agent("security", SecurityStub())


def test_security_gate_fail_escalates_at_limit(ctx):
    """A security stub that always blocks should hit FAILED after sec_max retries."""
    from orchestrator.stubs.tester_stub import TesterStub
    from orchestrator.stubs.security_stub import SecurityStub

    class AlwaysBlockedSecurity(SecurityStub):
        def __init__(self):
            super().__init__(fail_first=True)
            self._call_count = 0
        def run(self, context):
            self._call_count += 1
            from datetime import datetime, timezone
            return AgentResult(
                agent="security_agent",
                status=AgentStatus.FAIL,
                summary="always blocked",
                data={"verdict": "BLOCKED",
                      "counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
                      "findings": [{"id": "SEC-X", "severity": "high",
                                    "type": "injection", "location": "x.py:1",
                                    "description": "test", "recommended_fix": "fix"}]},
                duration_seconds=0.01,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    agents_base.register_agent("test", TesterStub(fail_first=False))
    agents_base.register_agent("security", AlwaysBlockedSecurity())

    result = run_pipeline(
        idea="test idea",
        project_id="sec_esc_test",
        auto_approve=True,
        demo_mode=False,
    )
    assert result.status == ProjectStatus.FAILED

    # Restore
    from orchestrator.stubs.tester_stub import TesterStub as TS
    from orchestrator.stubs.security_stub import SecurityStub as SS
    agents_base.register_agent("test", TS())
    agents_base.register_agent("security", SS())


# ─── Gate rules ───────────────────────────────────────────────────────────────

class TestPlanGate:
    def test_pass(self, ctx):
        data = {
            "requirements": [{"id": f"R{i}"} for i in range(6)],
            "architecture": {"adr": [{"id": "ADR-001"}]},
        }
        r = _agent_result("PASS", data)
        gr = evaluate_plan_gate(r, ctx)
        assert gr.verdict == GateVerdict.PASS

    def test_fail_too_few_requirements(self, ctx):
        data = {
            "requirements": [{"id": "R1"}],
            "architecture": {"adr": [{"id": "ADR-001"}]},
        }
        r = _agent_result("PASS", data)
        gr = evaluate_plan_gate(r, ctx)
        assert gr.verdict == GateVerdict.FAIL
        assert "user stories" in gr.reason

    def test_fail_no_adr(self, ctx):
        data = {
            "requirements": [{"id": f"R{i}"} for i in range(6)],
            "architecture": {"adr": []},
        }
        r = _agent_result("PASS", data)
        gr = evaluate_plan_gate(r, ctx)
        assert gr.verdict == GateVerdict.FAIL
        assert "ADR" in gr.reason

    def test_fail_agent_error(self, ctx):
        r = _agent_result("ERROR")
        gr = evaluate_plan_gate(r, ctx)
        assert gr.verdict == GateVerdict.FAIL


class TestTestGate:
    def test_pass_all(self, ctx):
        r = _agent_result("PASS", {"total": 20, "passed": 20, "failed": 0,
                                    "failures": [], "coverage_percent": 85.0})
        gr = evaluate_test_gate(r, ctx, "ms_001")
        assert gr.verdict == GateVerdict.PASS

    def test_fail_partial(self, ctx):
        r = _agent_result("FAIL", {"total": 20, "passed": 17, "failed": 3,
                                    "failures": [{"test": "t1", "error": "e"}],
                                    "coverage_percent": 72.0})
        gr = evaluate_test_gate(r, ctx, "ms_001")
        assert gr.verdict == GateVerdict.FAIL
        assert "17/20" in gr.reason

    def test_fail_agent_error(self, ctx):
        r = _agent_result("ERROR")
        gr = evaluate_test_gate(r, ctx, "ms_001")
        assert gr.verdict == GateVerdict.FAIL


class TestSecurityGate:
    def test_pass_no_findings(self, ctx):
        r = _agent_result("PASS", {"verdict": "PASS",
                                    "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                                    "findings": []})
        gr = evaluate_security_gate(r, ctx, "ms_001")
        assert gr.verdict == GateVerdict.PASS

    def test_blocked_high_finding(self, ctx):
        r = _agent_result("FAIL", {
            "verdict": "BLOCKED",
            "counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            "findings": [{"id": "SEC-001", "severity": "high",
                           "type": "broken_access_control",
                           "location": "tasks.py:54",
                           "description": "no ownership check",
                           "recommended_fix": "add check"}],
        })
        gr = evaluate_security_gate(r, ctx, "ms_001")
        assert gr.verdict == GateVerdict.BLOCKED
        assert "HIGH" in gr.reason

    def test_blocked_critical_finding(self, ctx):
        r = _agent_result("FAIL", {
            "verdict": "BLOCKED",
            "counts": {"critical": 1, "high": 0, "medium": 0, "low": 0},
            "findings": [{"id": "SEC-002", "severity": "critical",
                           "type": "injection",
                           "location": "db.py:10",
                           "description": "SQL injection",
                           "recommended_fix": "use parameterised queries"}],
        })
        gr = evaluate_security_gate(r, ctx, "ms_001")
        assert gr.verdict == GateVerdict.BLOCKED

    def test_medium_does_not_block(self, ctx):
        r = _agent_result("PASS", {
            "verdict": "PASS",
            "counts": {"critical": 0, "high": 0, "medium": 2, "low": 1},
            "findings": [],
        })
        gr = evaluate_security_gate(r, ctx, "ms_001")
        assert gr.verdict == GateVerdict.PASS


class TestReleaseGate:
    def test_fail_not_approved(self, ctx):
        gr = evaluate_release_gate(ctx)
        assert gr.verdict == GateVerdict.FAIL

    def test_pass_when_approved(self, ctx):
        ctx.human_approved_release = True
        gr = evaluate_release_gate(ctx)
        assert gr.verdict == GateVerdict.PASS


# ─── End-to-end: straight pass (no demo loops) ────────────────────────────────

def test_e2e_no_demo_loops():
    """Full pipeline, stubs always pass, auto_approve=True → RELEASED."""
    from orchestrator.stubs.tester_stub import TesterStub
    from orchestrator.stubs.security_stub import SecurityStub
    agents_base.register_agent("test",     TesterStub(fail_first=False))
    agents_base.register_agent("security", SecurityStub(fail_first=False))

    result = run_pipeline(
        idea="e2e straight pass test",
        project_id="e2e_pass",
        auto_approve=True,
        demo_mode=False,
    )
    assert result.status == ProjectStatus.RELEASED
    assert result.human_approved_arch is True
    assert result.human_approved_release is True
    assert len(result.milestones) == 1
    assert result.milestones[0].status.value == "approved"

    # Restore
    agents_base.register_agent("test",     TesterStub())
    agents_base.register_agent("security", SecurityStub())


# ─── End-to-end: demo mode (fail first, then pass) ────────────────────────────

def test_e2e_demo_mode():
    """Full pipeline in demo mode: test fails once, security blocks once → both fixed → RELEASED."""
    from orchestrator.stubs.tester_stub import TesterStub
    from orchestrator.stubs.security_stub import SecurityStub
    agents_base.register_agent("test",     TesterStub(fail_first=True))
    agents_base.register_agent("security", SecurityStub(fail_first=True))

    result = run_pipeline(
        idea="demo mode e2e test",
        project_id="e2e_demo",
        auto_approve=True,
        demo_mode=True,
    )
    assert result.status == ProjectStatus.RELEASED
    assert result.retries["test"] >= 1
    assert result.retries["security"] >= 1

    # Restore
    agents_base.register_agent("test",     TesterStub())
    agents_base.register_agent("security", SecurityStub())
