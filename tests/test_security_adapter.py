"""Tests for the connection between the orchestrator and the security agent."""
import shutil
from pathlib import Path

from orchestrator.adapters.security_adapter import SecurityAdapter
from orchestrator.contracts import AgentStatus, ProjectContext
from orchestrator.gates import evaluate_security_gate

ROOT = Path(__file__).resolve().parent.parent
BUGGY = ROOT / "tests" / "fixtures" / "demo_bug_original.py"


def _context() -> ProjectContext:
    return ProjectContext(project_id="p1", idea="x", created_at="2026-09-26T00:00:00Z")


def _adapter_for(tmp_path, source_text: str) -> SecurityAdapter:
    target = ROOT / "backend" / "_security_test_target.py"
    target.write_text(source_text, encoding="utf-8")
    return SecurityAdapter(scan_path="backend/_security_test_target.py"), target


def test_buggy_demo_file_is_blocked_with_a_high_finding(tmp_path):
    adapter, target = _adapter_for(tmp_path, BUGGY.read_text(encoding="utf-8"))
    try:
        result = adapter.run(_context())
    finally:
        target.unlink()
    assert result.status == AgentStatus.FAIL
    assert result.data["verdict"] == "BLOCKED"
    assert result.data["counts"]["high"] >= 1
    finding = result.data["findings"][0]
    assert finding["severity"] == "high"
    assert finding["type"] == "broken_access_control"
    gate = evaluate_security_gate(result, _context())
    assert gate.verdict.value == "BLOCKED"


def test_fixed_demo_file_passes(tmp_path):
    fixed = BUGGY.read_text(encoding="utf-8").replace(
        "    # BUG: no ownership check — any user can delete any task\n",
        "    if task.owner_id != current_user.id:\n        raise HTTPException(status_code=403, detail='Not authorized')\n",
    )
    assert "owner_id != current_user.id" in fixed
    adapter, target = _adapter_for(tmp_path, fixed)
    try:
        result = adapter.run(_context())
    finally:
        target.unlink()
    assert result.status == AgentStatus.PASS
    assert evaluate_security_gate(result, _context()).verdict.value == "PASS"


def test_missing_scan_target_returns_error_not_pass():
    result = SecurityAdapter(scan_path="backend/does_not_exist.py").run(_context())
    assert result.status == AgentStatus.ERROR
    assert evaluate_security_gate(result, _context()).verdict.value == "BLOCKED"
