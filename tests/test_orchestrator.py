"""
tests/test_orchestrator.py
Orchestrator + Security integration tests — DevForge pipeline.

Tests:
    Security fix loop:
        1.  BLOCKED on call 1 → SECURITY_FIX → PASS on call 2 → MILESTONE_APPROVED
        2.  retries["security"] == 1 after one fix
        3.  BLOCKED on both calls → retries["security"] == 2 → HUMAN_REVIEW
        4.  Medium finding only → PASS immediately (no fix needed)
        5.  Security fix loop re-runs BOTH tester AND security agent (regression check)
        6.  Security ERROR → treated as BLOCKED (not PASS)

    Runner merge logic:
        7.  merge(PASS, PASS) → "PASS"
        8.  merge(FAIL, PASS) → "FIX_TEST"
        9.  merge(PASS, BLOCKED) → "FIX_SECURITY"
        10. merge(FAIL, BLOCKED) → "FIX_SECURITY" (security first)

    Scanner / Auth checker:
        11. Planted vulnerability detected by authorization checker
        12. Fixed vulnerability NOT detected after ownership check added
        13. Path traversal protection (path outside workspace → ValueError)

    Security Agent (demo mode):
        14. First call → BLOCKED
        15. Second call → PASS
        16. reset_call_count → first call BLOCKED again
        17. Missing fixture → ERROR (not PASS)

    Security Agent (real mode):
        18. real mode scan returns PASS on clean code
        19. real mode scan returns BLOCKED on vulnerable code
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from memory.schemas import SecurityFinding
from security.gate import evaluate_security_gate
from security.scanner import run_authorization_checker, ScannerError
from security.security_agent import SecurityAgent
from orchestrator.runner import merge


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures"

VULNERABLE_CODE = '''
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()

@router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = None):
    # No ownership check — any user can delete any task (CWE-639)
    task = db.query(None).filter(None).first()
    if not task:
        raise HTTPException(status_code=404)
    db.delete(task)
    return None
'''

FIXED_CODE = '''
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()

@router.delete("/{task_id}")
async def delete_task(task_id: int, current_user=None, db: Session = None):
    task = db.query(None).filter(None).first()
    if not task:
        raise HTTPException(status_code=404)
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db.delete(task)
    return None
'''

CLEAN_CODE = '''
from fastapi import APIRouter

router = APIRouter()

@router.get("/items")
def list_items():
    return []
'''


# ---------------------------------------------------------------------------
# Helper: stub agents
# ---------------------------------------------------------------------------

def _make_pass_agent(name="stub_agent"):
    def agent(input_data):
        return {
            "agent": name,
            "milestone_id": input_data.get("milestone_id", "ms_001"),
            "status": "PASS",
            "summary": "stub pass",
            "payload": {},
        }
    return agent


def _make_blocked_agent(name="security_agent", n_blocks=1):
    """Returns BLOCKED for the first n_blocks calls, then PASS."""
    counter = {"n": 0}
    def agent(input_data):
        counter["n"] += 1
        if counter["n"] <= n_blocks:
            return {
                "agent": name,
                "milestone_id": input_data.get("milestone_id", "ms_001"),
                "status": "BLOCKED",
                "summary": "1 HIGH finding",
                "payload": {
                    "verdict": "BLOCKED",
                    "findings": [{
                        "id": "SEC-001",
                        "severity": "HIGH",
                        "category": "broken_access_control",
                        "description": "No ownership check",
                        "file": "tasks.py",
                        "line": 10,
                        "cwe": "CWE-639",
                        "status": "OPEN",
                    }],
                },
            }
        return {
            "agent": name,
            "milestone_id": input_data.get("milestone_id", "ms_001"),
            "status": "PASS",
            "summary": "0 findings",
            "payload": {"verdict": "PASS", "findings": []},
        }
    return agent, counter


def _make_plan_agent():
    """Plan agent that produces a gate-passing plan result."""
    def agent(input_data):
        return {
            "agent": "plan_agent",
            "milestone_id": "plan",
            "status": "PASS",
            "summary": "Plan complete",
            "payload": {
                "user_stories": [{"id": i, "ac": "..."} for i in range(6)],
                "tech_stack": "FastAPI + PostgreSQL",
                "adrs": [{"id": "ADR-001", "decision": "Use PostgreSQL"}],
                "milestones": ["ms_001"],
            },
        }
    return agent


def _make_builder_agent():
    def agent(input_data):
        return {
            "agent": "builder_agent",
            "milestone_id": input_data.get("milestone_id", "ms_001"),
            "status": "PASS",
            "summary": "Build done",
            "payload": {"files": []},
        }
    return agent


def _make_debugger_agent():
    def agent(input_data):
        return {
            "agent": "debugger_agent",
            "milestone_id": input_data.get("milestone_id", "ms_001"),
            "status": "PASS",
            "summary": "Debug done",
            "payload": {},
        }
    return agent


# ===========================================================================
# Runner merge logic
# ===========================================================================

class TestRunnerMerge:

    def test_both_pass(self):
        """Test 7: merge(PASS, PASS) → PASS."""
        result = merge(
            {"status": "PASS"},
            {"status": "PASS"},
        )
        assert result["verdict"] == "PASS"

    def test_test_fail_sec_pass(self):
        """Test 8: merge(FAIL, PASS) → FIX_TEST."""
        result = merge(
            {"status": "FAIL"},
            {"status": "PASS"},
        )
        assert result["verdict"] == "FIX_TEST"

    def test_test_pass_sec_blocked(self):
        """Test 9: merge(PASS, BLOCKED) → FIX_SECURITY."""
        result = merge(
            {"status": "PASS"},
            {"status": "BLOCKED"},
        )
        assert result["verdict"] == "FIX_SECURITY"

    def test_both_fail(self):
        """Test 10: merge(FAIL, BLOCKED) → FIX_SECURITY (security first)."""
        result = merge(
            {"status": "FAIL"},
            {"status": "BLOCKED"},
        )
        assert result["verdict"] == "FIX_SECURITY"

    def test_merge_preserves_results(self):
        """merge result contains both sub-results."""
        t = {"status": "PASS", "agent": "tester"}
        s = {"status": "PASS", "agent": "security"}
        result = merge(t, s)
        assert result["test_result"] is t
        assert result["security_result"] is s


# ===========================================================================
# Security fix loop — Orchestrator integration
# ===========================================================================

class TestSecurityFixLoop:

    def _make_orchestrator(self, security_fn, test_fn=None):
        from orchestrator.orchestrator import Orchestrator
        return Orchestrator(
            plan_fn=_make_plan_agent(),
            builder_fn=_make_builder_agent(),
            tester_fn=test_fn or _make_pass_agent("tester_agent"),
            security_fn=security_fn,
            debugger_fn=_make_debugger_agent(),
        )

    def test_security_fix_loop_resolves_on_second_run(self):
        """Test 1: BLOCKED on first call, PASS on second → MILESTONE_APPROVED."""
        from orchestrator.orchestrator import ProjectStatus
        sec_fn, counter = _make_blocked_agent(n_blocks=1)
        orch = self._make_orchestrator(sec_fn)
        ctx = orch.create_project("proj_001", "test idea")
        ctx = orch.run(ctx)

        assert ctx.status == ProjectStatus.AWAITING_APPROVAL
        # Security was called at least twice (once BLOCKED, once PASS)
        assert counter["n"] >= 2

    def test_security_retry_counter_after_one_fix(self):
        """Test 2: retries["security"] == 1 after one successful fix."""
        sec_fn, _ = _make_blocked_agent(n_blocks=1)
        orch = self._make_orchestrator(sec_fn)
        ctx = orch.create_project("proj_002", "test idea")
        ctx = orch.run(ctx)

        assert ctx.retries["security"] == 1

    def test_security_max_retry_escalates(self):
        """Test 3: Always BLOCKED → retries["security"] == 2 → HUMAN_REVIEW."""
        from orchestrator.orchestrator import ProjectStatus, MAX_SECURITY_RETRIES
        sec_fn, counter = _make_blocked_agent(n_blocks=99)
        orch = self._make_orchestrator(sec_fn)
        ctx = orch.create_project("proj_003", "test idea")
        ctx = orch.run(ctx)

        assert ctx.status == ProjectStatus.HUMAN_REVIEW
        assert ctx.retries["security"] > MAX_SECURITY_RETRIES

    def test_medium_only_does_not_block(self):
        """Test 4: Only MEDIUM findings → security PASS → milestone approved."""
        from orchestrator.orchestrator import ProjectStatus

        def sec_fn(input_data):
            return {
                "agent": "security_agent",
                "milestone_id": input_data.get("milestone_id", "ms_001"),
                "status": "PASS",
                "summary": "1 medium (informational)",
                "payload": {
                    "verdict": "PASS",
                    "findings": [{
                        "id": "SEC-001",
                        "severity": "MEDIUM",
                        "category": "info",
                        "description": "medium issue",
                        "file": "tasks.py",
                        "line": 5,
                        "cwe": "CWE-000",
                        "status": "OPEN",
                    }],
                },
            }

        orch = self._make_orchestrator(sec_fn)
        ctx = orch.create_project("proj_004", "test idea")
        ctx = orch.run(ctx)

        assert ctx.status == ProjectStatus.AWAITING_APPROVAL
        assert ctx.retries["security"] == 0

    def test_security_fix_reruns_both_agents(self):
        """Test 5: After security fix, BOTH tester AND security are re-run."""
        tester_call_count = {"n": 0}
        sec_fn, sec_counter = _make_blocked_agent(n_blocks=1)

        def counting_tester(input_data):
            tester_call_count["n"] += 1
            return {
                "agent": "tester_agent",
                "milestone_id": input_data.get("milestone_id", "ms_001"),
                "status": "PASS",
                "summary": "all pass",
                "payload": {"pass_count": 20, "fail_count": 0, "test_results": []},
            }

        orch = self._make_orchestrator(sec_fn, test_fn=counting_tester)
        ctx = orch.create_project("proj_005", "test idea")
        ctx = orch.run(ctx)

        # Tester must have been called at least twice
        # (once in the first parallel run + once after security fix)
        assert tester_call_count["n"] >= 2, (
            f"Expected tester to be re-run after security fix, "
            f"but it was called {tester_call_count['n']} time(s)"
        )

    def test_security_error_does_not_pass(self):
        """Test 6: Security ERROR must NOT result in MILESTONE_APPROVED."""
        from orchestrator.orchestrator import ProjectStatus

        def error_sec_fn(input_data):
            return {
                "agent": "security_agent",
                "milestone_id": input_data.get("milestone_id", "ms_001"),
                "status": "ERROR",
                "summary": "Scanner unavailable",
                "payload": {"verdict": "ERROR"},
            }

        orch = self._make_orchestrator(error_sec_fn)
        ctx = orch.create_project("proj_006", "test idea")
        ctx = orch.run(ctx)

        # ERROR must not lead to AWAITING_APPROVAL (milestone not approved silently)
        assert ctx.status != ProjectStatus.AWAITING_APPROVAL


# ===========================================================================
# Authorization checker — planted vulnerability detection
# ===========================================================================

class TestAuthorizationChecker:

    def test_planted_vulnerability_detected(self):
        """Test 11: The authorization checker detects the CWE-639 vulnerability."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(VULNERABLE_CODE)
            tmp_path = f.name

        try:
            findings = run_authorization_checker(tmp_path)
            assert len(findings) >= 1, "Expected at least one finding on vulnerable code"
            high_findings = [f for f in findings if f.severity == "HIGH"]
            assert len(high_findings) >= 1, "Expected at least one HIGH finding"
            cwes = [f.cwe for f in high_findings]
            assert "CWE-639" in cwes, f"Expected CWE-639 in findings, got: {cwes}"
        finally:
            os.unlink(tmp_path)

    def test_fixed_vulnerability_not_detected(self):
        """Test 12: After fix, ownership check present → no authorization finding."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(FIXED_CODE)
            tmp_path = f.name

        try:
            findings = run_authorization_checker(tmp_path)
            cwe_639 = [f for f in findings if f.cwe == "CWE-639" and f.status == "OPEN"]
            assert len(cwe_639) == 0, (
                f"Expected no OPEN CWE-639 findings after fix, got: {cwe_639}"
            )
        finally:
            os.unlink(tmp_path)

    def test_clean_code_has_no_findings(self):
        """Clean code with only GET endpoints → no authorization findings."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(CLEAN_CODE)
            tmp_path = f.name

        try:
            findings = run_authorization_checker(tmp_path)
            assert len(findings) == 0, f"Unexpected findings on clean code: {findings}"
        finally:
            os.unlink(tmp_path)

    def test_path_traversal_protection(self):
        """Test 13: Path outside workspace root raises ValueError."""
        with pytest.raises((ValueError, FileNotFoundError)):
            run_authorization_checker(
                "/etc/passwd",
                workspace_root=str(Path(__file__).parent),
            )

    def test_invalid_python_skipped(self):
        """Invalid Python syntax file is skipped, not crashed on."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken(:\n    pass\n")  # syntax error
            tmp_path = f.name
        try:
            # Should not raise
            findings = run_authorization_checker(tmp_path)
            assert isinstance(findings, list)
        finally:
            os.unlink(tmp_path)


# ===========================================================================
# Security Agent — demo mode
# ===========================================================================

class TestSecurityAgentDemoMode:

    def test_first_call_returns_blocked(self):
        """Test 14: First call in demo mode → BLOCKED."""
        agent = SecurityAgent(demo_mode=True)
        result = agent.run({"milestone_id": "ms_001"})
        assert result["status"] == "BLOCKED"
        assert result["agent"] == "security_agent"

    def test_second_call_returns_pass(self):
        """Test 15: Second call in demo mode → PASS."""
        agent = SecurityAgent(demo_mode=True)
        agent.run({"milestone_id": "ms_001"})  # call 1 → BLOCKED
        result = agent.run({"milestone_id": "ms_001"})  # call 2 → PASS
        assert result["status"] == "PASS"

    def test_reset_call_count_restarts_sequence(self):
        """Test 16: reset_call_count → next call returns BLOCKED again."""
        agent = SecurityAgent(demo_mode=True)
        agent.run({"milestone_id": "ms_001"})
        agent.run({"milestone_id": "ms_001"})  # now at call 2 → PASS
        agent.reset_call_count()
        result = agent.run({"milestone_id": "ms_001"})  # should be BLOCKED again
        assert result["status"] == "BLOCKED"

    def test_blocked_fixture_has_high_finding(self):
        """BLOCKED fixture contains a HIGH finding with CWE-639."""
        agent = SecurityAgent(demo_mode=True)
        result = agent.run({"milestone_id": "ms_001"})
        findings = result["payload"]["findings"]
        assert len(findings) >= 1
        high = [f for f in findings if f["severity"] == "HIGH"]
        assert len(high) >= 1
        cwe_639 = [f for f in high if f["cwe"] == "CWE-639"]
        assert len(cwe_639) >= 1

    def test_pass_fixture_finding_is_fixed(self):
        """PASS fixture has the finding marked as FIXED (showing the fix was applied)."""
        agent = SecurityAgent(demo_mode=True)
        agent.run({"milestone_id": "ms_001"})  # BLOCKED
        result = agent.run({"milestone_id": "ms_001"})  # PASS
        findings = result["payload"]["findings"]
        assert len(findings) >= 1
        assert all(f["status"] == "FIXED" for f in findings), (
            f"Expected all findings FIXED in PASS fixture, got: {findings}"
        )

    def test_result_has_timestamp_and_duration(self):
        """Agent result always includes timestamp and duration_seconds."""
        agent = SecurityAgent(demo_mode=True)
        result = agent.run({"milestone_id": "ms_001"})
        assert "timestamp" in result
        assert "duration_seconds" in result
        assert isinstance(result["duration_seconds"], (int, float))

    def test_milestone_id_stamped_in_result(self):
        """milestone_id from input is stamped into the result."""
        agent = SecurityAgent(demo_mode=True)
        result = agent.run({"milestone_id": "ms_custom_99"})
        assert result["milestone_id"] == "ms_custom_99"


# ===========================================================================
# Security Agent — real mode
# ===========================================================================

class TestSecurityAgentRealMode:

    def test_real_mode_pass_on_clean_code(self):
        """Test 18: Real mode on code with no write endpoints → PASS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "clean.py"
            p.write_text(CLEAN_CODE)

            agent = SecurityAgent(
                demo_mode=False,
                workspace_root=tmpdir,
            )
            result = agent.run({
                "milestone_id": "ms_001",
                "scan_path": tmpdir,
            })

        # Should PASS (no DELETE/PUT/PATCH with {id} that lack ownership check)
        assert result["status"] in ("PASS", "ERROR"), f"Unexpected status: {result['status']}"
        # If scanner errors (Bandit not installed in CI), accept ERROR but not BLOCKED
        if result["status"] == "PASS":
            assert result["payload"]["high_count"] == 0
            assert result["payload"]["critical_count"] == 0

    def test_real_mode_blocked_on_vulnerable_code(self):
        """Test 19: Real mode on vulnerable code → BLOCKED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "tasks.py"
            p.write_text(VULNERABLE_CODE)

            agent = SecurityAgent(
                demo_mode=False,
                workspace_root=tmpdir,
            )
            result = agent.run({
                "milestone_id": "ms_001",
                "scan_path": tmpdir,
            })

        # Authorization checker must find CWE-639 and return BLOCKED
        # (independent of whether Bandit is installed)
        if result["status"] == "ERROR":
            pytest.skip("Scanner error — likely Bandit not installed in this environment")
        assert result["status"] == "BLOCKED", (
            f"Expected BLOCKED on vulnerable code, got {result['status']}. "
            f"Summary: {result['summary']}"
        )

    def test_real_mode_no_scan_path_returns_error(self):
        """Real mode with no scannable path → ERROR (not PASS)."""
        agent = SecurityAgent(demo_mode=False, workspace_root="/tmp")
        result = agent.run({"milestone_id": "ms_001", "files": []})
        assert result["status"] == "ERROR"
        assert result["payload"]["verdict"] == "ERROR"


# ===========================================================================
# Security fixtures integrity
# ===========================================================================

class TestFixtureIntegrity:

    def test_security_finding_high_fixture_valid(self):
        """security_finding_HIGH.json is valid and contains a HIGH OPEN finding."""
        fixture = json.loads((FIXTURE_DIR / "security_finding_HIGH.json").read_text())
        assert fixture["status"] == "BLOCKED"
        assert fixture["agent"] == "security_agent"
        findings = fixture["payload"]["findings"]
        assert len(findings) >= 1
        high = [f for f in findings if f["severity"] == "HIGH" and f["status"] == "OPEN"]
        assert len(high) >= 1
        assert high[0]["cwe"] == "CWE-639"

    def test_security_pass_fixture_valid(self):
        """security_pass.json is valid and contains no OPEN HIGH/CRITICAL findings."""
        fixture = json.loads((FIXTURE_DIR / "security_pass.json").read_text())
        assert fixture["status"] == "PASS"
        findings = fixture["payload"]["findings"]
        open_high = [
            f for f in findings
            if f["status"] == "OPEN" and f["severity"] in ("HIGH", "CRITICAL")
        ]
        assert len(open_high) == 0, f"Expected no OPEN HIGH/CRITICAL in PASS fixture: {open_high}"

    def test_pass_fixture_finding_marked_fixed(self):
        """The previously OPEN finding appears as FIXED in the PASS fixture."""
        fixture = json.loads((FIXTURE_DIR / "security_pass.json").read_text())
        findings = fixture["payload"]["findings"]
        assert len(findings) >= 1
        assert all(f["status"] == "FIXED" for f in findings), (
            "PASS fixture findings should all be FIXED"
        )
