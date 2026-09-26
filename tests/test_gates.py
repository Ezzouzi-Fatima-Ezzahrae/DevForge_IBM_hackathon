"""
tests/test_gates.py
Security gate unit tests — DevForge pipeline.

Tests:
    1.  No findings → PASS
    2.  HIGH (OPEN) → BLOCKED
    3.  CRITICAL (OPEN) → BLOCKED
    4.  MEDIUM only → PASS
    5.  LOW only → PASS
    6.  HIGH but FIXED → PASS
    7.  CRITICAL + HIGH + MEDIUM → BLOCKED with correct counts
    8.  Mixed MEDIUM + HIGH → BLOCKED
    9.  Gate details contain correct counts
    10. Gate milestone_id is preserved
    11. Multiple CRITICAL → BLOCKED, count correct
    12. INFO only → PASS
    13. evaluate_security_gate_from_result — PASS flow
    14. evaluate_security_gate_from_result — BLOCKED flow
    15. evaluate_security_gate_from_result — ERROR from scanner
    16. Test gate PASS (≥80%, 0 critical failures)
    17. Test gate FAIL (< 80%)
    18. Test gate FAIL (critical path failure)
    19. Plan gate PASS
    20. Plan gate FAIL
"""
from __future__ import annotations

import pytest
from memory.schemas import GateResult, SecurityFinding
from security.gate import evaluate_security_gate
from orchestrator.gates import evaluate_security_gate_from_result, evaluate_test_gate, evaluate_plan_gate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(
    severity: str,
    status: str = "OPEN",
    finding_id: str = "SEC-001",
    cwe: str = "CWE-000",
) -> SecurityFinding:
    return SecurityFinding(
        id=finding_id,
        severity=severity,
        category="test_category",
        description="Test finding",
        file="test_file.py",
        line=1,
        cwe=cwe,
        status=status,
    )


def _agent_result(findings: list, status: str = "PASS") -> dict:
    """Build a minimal AgentResult dict as produced by security_agent.run()."""
    return {
        "agent": "security_agent",
        "milestone_id": "ms_001",
        "status": status,
        "summary": "test",
        "payload": {
            "verdict": status,
            "findings": [f.model_dump() for f in findings],
        },
    }


# ===========================================================================
# Security gate — core logic
# ===========================================================================

class TestSecurityGateCoreLogic:

    def test_no_findings_passes(self):
        """Test 1: Zero findings → PASS."""
        result = evaluate_security_gate([], "ms_001")
        assert result.verdict == "PASS"
        assert result.gate == "security"
        assert result.milestone_id == "ms_001"

    def test_high_open_blocks(self):
        """Test 2: One HIGH OPEN finding → BLOCKED."""
        result = evaluate_security_gate([_finding("HIGH")], "ms_001")
        assert result.verdict == "BLOCKED"

    def test_critical_open_blocks(self):
        """Test 3: One CRITICAL OPEN finding → BLOCKED."""
        result = evaluate_security_gate([_finding("CRITICAL")], "ms_001")
        assert result.verdict == "BLOCKED"

    def test_medium_only_passes(self):
        """Test 4: MEDIUM only → PASS (medium does not block)."""
        result = evaluate_security_gate([_finding("MEDIUM")], "ms_001")
        assert result.verdict == "PASS"

    def test_low_only_passes(self):
        """Test 5: LOW only → PASS."""
        result = evaluate_security_gate([_finding("LOW")], "ms_001")
        assert result.verdict == "PASS"

    def test_high_fixed_passes(self):
        """Test 6: HIGH finding but status=FIXED → PASS (previous fix was applied)."""
        result = evaluate_security_gate([_finding("HIGH", status="FIXED")], "ms_001")
        assert result.verdict == "PASS"

    def test_critical_fixed_passes(self):
        """CRITICAL finding but status=FIXED → PASS."""
        result = evaluate_security_gate([_finding("CRITICAL", status="FIXED")], "ms_001")
        assert result.verdict == "PASS"

    def test_mixed_high_and_medium_blocks(self):
        """Test 8: MEDIUM + HIGH OPEN → BLOCKED."""
        result = evaluate_security_gate(
            [_finding("MEDIUM"), _finding("HIGH", finding_id="SEC-002")],
            "ms_001",
        )
        assert result.verdict == "BLOCKED"

    def test_mixed_counts_are_correct(self):
        """Test 7 / Test 9: CRITICAL + HIGH + MEDIUM → correct counts in details."""
        findings = [
            _finding("CRITICAL", finding_id="SEC-001"),
            _finding("HIGH",     finding_id="SEC-002"),
            _finding("MEDIUM",   finding_id="SEC-003"),
        ]
        result = evaluate_security_gate(findings, "ms_001")
        assert result.verdict == "BLOCKED"
        assert result.details["critical"] == 1
        assert result.details["high"] == 1
        assert result.details["medium"] == 1
        assert result.details["total_open"] == 3

    def test_milestone_id_preserved(self):
        """Test 10: Gate result carries the correct milestone_id."""
        result = evaluate_security_gate([], "ms_999")
        assert result.milestone_id == "ms_999"

    def test_multiple_critical_count(self):
        """Test 11: Multiple CRITICAL findings — all counted."""
        findings = [
            _finding("CRITICAL", finding_id="SEC-001"),
            _finding("CRITICAL", finding_id="SEC-002"),
            _finding("CRITICAL", finding_id="SEC-003"),
        ]
        result = evaluate_security_gate(findings, "ms_001")
        assert result.verdict == "BLOCKED"
        assert result.details["critical"] == 3

    def test_info_only_passes(self):
        """Test 12: INFO severity does not block."""
        result = evaluate_security_gate([_finding("INFO")], "ms_001")
        assert result.verdict == "PASS"

    def test_many_medium_zero_high_passes(self):
        """Many MEDIUM open, 0 HIGH/CRITICAL → PASS."""
        findings = [_finding("MEDIUM", finding_id=f"SEC-{i:03d}") for i in range(10)]
        result = evaluate_security_gate(findings, "ms_001")
        assert result.verdict == "PASS"
        assert result.details["medium"] == 10

    def test_fixed_high_with_open_medium_passes(self):
        """FIXED HIGH + OPEN MEDIUM → PASS (only OPEN HIGH/CRITICAL block)."""
        findings = [
            _finding("HIGH",   status="FIXED", finding_id="SEC-001"),
            _finding("MEDIUM", status="OPEN",  finding_id="SEC-002"),
        ]
        result = evaluate_security_gate(findings, "ms_001")
        assert result.verdict == "PASS"

    def test_total_findings_includes_fixed(self):
        """total_findings includes both OPEN and FIXED; total_open is only OPEN."""
        findings = [
            _finding("HIGH",   status="FIXED", finding_id="SEC-001"),
            _finding("MEDIUM", status="OPEN",  finding_id="SEC-002"),
        ]
        result = evaluate_security_gate(findings, "ms_001")
        assert result.details["total_findings"] == 2
        assert result.details["total_open"] == 1

    def test_gate_returns_gateresult_instance(self):
        """evaluate_security_gate always returns a GateResult."""
        result = evaluate_security_gate([], "ms_001")
        assert isinstance(result, GateResult)


# ===========================================================================
# evaluate_security_gate_from_result — orchestrator integration
# ===========================================================================

class TestEvaluateSecurityGateFromResult:

    def test_pass_flow(self):
        """Test 13: AgentResult with PASS status → gate PASS."""
        agent_result = _agent_result([], status="PASS")
        result = evaluate_security_gate_from_result(agent_result)
        assert result.verdict == "PASS"

    def test_blocked_flow_with_high(self):
        """Test 14: AgentResult with BLOCKED + HIGH finding → gate BLOCKED."""
        findings = [_finding("HIGH")]
        agent_result = _agent_result(findings, status="BLOCKED")
        result = evaluate_security_gate_from_result(agent_result)
        assert result.verdict == "BLOCKED"

    def test_error_from_scanner(self):
        """Test 15: AgentResult with ERROR status → gate ERROR (not PASS)."""
        agent_result = {
            "agent": "security_agent",
            "milestone_id": "ms_001",
            "status": "ERROR",
            "summary": "Scanner crashed",
            "payload": {"error": "bandit not found"},
        }
        result = evaluate_security_gate_from_result(agent_result)
        assert result.verdict == "ERROR"
        assert result.verdict != "PASS"

    def test_fixed_high_in_payload_passes(self):
        """AgentResult with HIGH finding FIXED → gate PASS."""
        findings = [_finding("HIGH", status="FIXED")]
        agent_result = _agent_result(findings, status="PASS")
        result = evaluate_security_gate_from_result(agent_result)
        assert result.verdict == "PASS"

    def test_malformed_finding_skipped(self):
        """Malformed findings in payload are skipped, not crashed on."""
        agent_result = {
            "agent": "security_agent",
            "milestone_id": "ms_001",
            "status": "PASS",
            "summary": "",
            "payload": {
                "findings": [{"bad": "data"}],  # missing required fields
            },
        }
        # Should not raise — malformed findings are skipped
        result = evaluate_security_gate_from_result(agent_result)
        assert result.verdict in ("PASS", "BLOCKED", "ERROR")


# ===========================================================================
# Test gate
# ===========================================================================

class TestTestGate:

    def _test_result(self, pass_count: int, fail_count: int, critical_failures=None):
        test_results = []
        for i in range(fail_count):
            test_results.append({
                "id": f"test_{i}",
                "name": f"test_{i}",
                "status": "FAIL",
                "file": "test.py",
                "line": i + 1,
                "is_critical_path": (critical_failures or [i]) and i in (critical_failures or []),
            })
        return {
            "agent": "tester_agent",
            "milestone_id": "ms_001",
            "status": "PASS" if fail_count == 0 else "FAIL",
            "summary": f"{pass_count}/{pass_count + fail_count}",
            "payload": {
                "pass_count": pass_count,
                "fail_count": fail_count,
                "test_results": test_results,
            },
        }

    def test_test_gate_pass_80_percent(self):
        """Test 16: 80% pass rate, no critical failures → PASS."""
        result = evaluate_test_gate(self._test_result(16, 4))
        assert result.verdict == "PASS"

    def test_test_gate_pass_100_percent(self):
        """20/20 → PASS."""
        result = evaluate_test_gate(self._test_result(20, 0))
        assert result.verdict == "PASS"

    def test_test_gate_fail_below_80(self):
        """Test 17: 17/20 = 85% but we test fail case with 14/20 = 70%."""
        result = evaluate_test_gate(self._test_result(14, 6))
        assert result.verdict == "FAIL"
        assert result.details["pass_rate"] < 0.8

    def test_test_gate_fail_critical_path(self):
        """Test 18: ≥80% pass but critical path failure → FAIL."""
        # 17/20 = 85% but test 0 is critical
        result = evaluate_test_gate(self._test_result(17, 3, critical_failures=[0]))
        assert result.verdict == "FAIL"
        assert result.details["critical_failures"] >= 1

    def test_test_gate_no_tests_fail(self):
        """0 tests → FAIL (no tests is not PASS)."""
        result = evaluate_test_gate(self._test_result(0, 0))
        assert result.verdict == "FAIL"


# ===========================================================================
# Plan gate
# ===========================================================================

class TestPlanGate:

    def _plan_result(self, n_stories: int, stack: str, n_adrs: int):
        return {
            "agent": "plan_agent",
            "milestone_id": "plan",
            "status": "PASS",
            "summary": "",
            "payload": {
                "user_stories": [{"id": i, "ac": "..."} for i in range(n_stories)],
                "tech_stack": stack,
                "adrs": [{"id": i} for i in range(n_adrs)],
                "milestones": ["ms_001"],
            },
        }

    def test_plan_gate_pass(self):
        """Test 19: 5 stories, stack named, 1 ADR → PASS."""
        result = evaluate_plan_gate(self._plan_result(5, "FastAPI + PostgreSQL", 1))
        assert result.verdict == "PASS"

    def test_plan_gate_fail_too_few_stories(self):
        """Test 20: < 5 user stories → FAIL."""
        result = evaluate_plan_gate(self._plan_result(3, "FastAPI", 1))
        assert result.verdict == "FAIL"

    def test_plan_gate_fail_no_stack(self):
        """No tech stack → FAIL."""
        result = evaluate_plan_gate(self._plan_result(5, "", 1))
        assert result.verdict == "FAIL"

    def test_plan_gate_fail_no_adr(self):
        """0 ADRs → FAIL."""
        result = evaluate_plan_gate(self._plan_result(5, "FastAPI", 0))
        assert result.verdict == "FAIL"
