"""Edge cases for the quality gates (orchestrator/gates.py).

The basic pass/fail cases live in tests/test_orchestrator.py; this file covers the
boundaries that decide the demo: ERROR results, empty results, thresholds.
"""
from datetime import datetime, timezone

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
    evaluate_release_gate,
    evaluate_security_gate,
    evaluate_test_gate,
)


def _ctx():
    return ProjectContext(project_id="g", idea="i", status=ProjectStatus.IDLE, created_at="now")


def _res(status, data=None, summary="s"):
    return AgentResult(
        agent="a",
        status=status,
        summary=summary,
        data=data or {},
        duration_seconds=0.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _plan(n_reqs, n_adr, status=AgentStatus.PASS):
    return _res(status, {"requirements": [{"id": i} for i in range(n_reqs)],
                         "architecture": {"adr": [{"id": i} for i in range(n_adr)]}})


def _sec(findings, verdict="PASS", status=AgentStatus.PASS):
    return _res(status, {"verdict": verdict, "counts": {}, "findings": findings})


def _finding(sev):
    return {"id": "F", "severity": sev, "type": "x", "location": "f.py:1"}


# ── plan gate ────────────────────────────────────────────────────────────────
def test_plan_gate_boundary_five_stories_passes():
    assert evaluate_plan_gate(_plan(5, 1), _ctx()).verdict == GateVerdict.PASS


def test_plan_gate_four_stories_fails():
    assert evaluate_plan_gate(_plan(4, 1), _ctx()).verdict == GateVerdict.FAIL


def test_plan_gate_needs_an_adr():
    assert evaluate_plan_gate(_plan(6, 0), _ctx()).verdict == GateVerdict.FAIL


def test_plan_gate_fails_when_agent_not_pass():
    assert evaluate_plan_gate(_plan(6, 1, AgentStatus.ERROR), _ctx()).verdict == GateVerdict.FAIL


def test_plan_gate_empty_data_fails_without_crashing():
    assert evaluate_plan_gate(_res(AgentStatus.PASS), _ctx()).verdict == GateVerdict.FAIL


# ── tests gate ───────────────────────────────────────────────────────────────
def test_tests_gate_all_pass():
    r = _res(AgentStatus.PASS, {"total": 20, "passed": 20, "coverage_percent": 90})
    assert evaluate_test_gate(r, _ctx()).verdict == GateVerdict.PASS


def test_tests_gate_one_failure_fails():
    r = _res(AgentStatus.FAIL, {"total": 20, "passed": 19,
                                "failures": [{"test": "t", "error": "e"}]})
    g = evaluate_test_gate(r, _ctx())
    assert g.verdict == GateVerdict.FAIL and "19/20" in g.reason


def test_tests_gate_zero_tests_is_not_a_pass():
    r = _res(AgentStatus.PASS, {"total": 0, "passed": 0})
    assert evaluate_test_gate(r, _ctx()).verdict == GateVerdict.FAIL


def test_tests_gate_missing_data_is_not_a_pass():
    assert evaluate_test_gate(_res(AgentStatus.PASS), _ctx()).verdict == GateVerdict.FAIL


def test_tests_gate_agent_error_fails():
    assert evaluate_test_gate(_res(AgentStatus.ERROR, summary="timeout"), _ctx()).verdict == GateVerdict.FAIL


def test_tests_gate_milestone_id_is_kept():
    r = _res(AgentStatus.PASS, {"total": 1, "passed": 1})
    assert evaluate_test_gate(r, _ctx(), "ms_001").milestone_id == "ms_001"


# ── security gate ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("sev", ["critical", "high"])
def test_security_blocks_on_critical_and_high(sev):
    g = evaluate_security_gate(_sec([_finding(sev)]), _ctx())
    assert g.verdict == GateVerdict.BLOCKED and g.gate == GateName.SECURITY


@pytest.mark.parametrize("sev", ["medium", "low"])
def test_security_ignores_medium_and_low(sev):
    assert evaluate_security_gate(_sec([_finding(sev)]), _ctx()).verdict == GateVerdict.PASS


def test_security_blocks_when_agent_says_blocked_even_without_findings():
    assert evaluate_security_gate(_sec([], verdict="BLOCKED"), _ctx()).verdict == GateVerdict.BLOCKED


def test_security_missing_verdict_defaults_to_blocked():
    assert evaluate_security_gate(_res(AgentStatus.PASS), _ctx()).verdict == GateVerdict.BLOCKED


def test_security_agent_error_is_blocked_not_pass():
    assert evaluate_security_gate(_res(AgentStatus.ERROR), _ctx()).verdict == GateVerdict.BLOCKED


def test_security_low_finding_next_to_high_still_blocks():
    g = evaluate_security_gate(_sec([_finding("low"), _finding("high")]), _ctx())
    assert g.verdict == GateVerdict.BLOCKED and "1 blocking" in g.reason


# ── release gate ─────────────────────────────────────────────────────────────
def test_release_gate_needs_human_approval():
    c = _ctx()
    assert evaluate_release_gate(c).verdict == GateVerdict.FAIL
    c.human_approved_release = True
    assert evaluate_release_gate(c).verdict == GateVerdict.PASS
