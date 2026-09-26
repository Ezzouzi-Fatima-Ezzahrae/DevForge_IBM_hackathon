"""Tests: the orchestrator records decisions, gate results and metrics in memory/."""
import json
import uuid

import pytest

from memory import memory_agent, metrics
from orchestrator import agents_base
from orchestrator.contracts import AgentResult, AgentStatus, GateName, GateResult, GateVerdict
from orchestrator.recorder import Recorder
from orchestrator.runner import run_pipeline
from orchestrator.stubs.builder_stub import BuilderStub
from orchestrator.stubs.debug_stub import DebugStub
from orchestrator.stubs.fix_stub import FixStub
from orchestrator.stubs.plan_stub import PlanStub
from orchestrator.stubs.security_stub import SecurityStub
from orchestrator.stubs import tester_stub


@pytest.fixture()
def memory_on(tmp_path, monkeypatch):
    """Switch recording on and redirect every memory file to a temp folder."""
    monkeypatch.setenv("DEVFORGE_MEMORY", "on")
    monkeypatch.setattr(metrics, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(metrics, "_METRICS_FILE", tmp_path / "metrics.json")
    monkeypatch.setattr(memory_agent, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(memory_agent, "_DECISIONS_FILE", tmp_path / "decisions.json")
    monkeypatch.setattr(memory_agent, "_GATE_RESULTS_FILE", tmp_path / "gate_results.json")
    return tmp_path


@pytest.fixture()
def stub_agents():
    """Use only stub agents (no real pytest run, no file patching), then restore the registry."""
    saved = dict(agents_base._registry)
    agents_base.register_agent("plan", PlanStub())
    agents_base.register_agent("build", BuilderStub())
    agents_base.register_agent("test", tester_stub.TesterStub(fail_first=True))
    agents_base.register_agent("debug", DebugStub())
    agents_base.register_agent("security", SecurityStub(fail_first=True))
    agents_base.register_agent("fix", FixStub())
    yield
    agents_base._registry.clear()
    agents_base._registry.update(saved)


def _pid() -> str:
    return f"test_{uuid.uuid4().hex[:8]}"


def test_full_run_records_metrics_decisions_and_gates(memory_on, stub_agents):
    pid = _pid()
    ctx = run_pipeline("task management SaaS", project_id=pid, auto_approve=True, demo_mode=True)
    assert ctx.status.value == "RELEASED"

    summary = metrics.get_summary(pid)
    assert summary["retry_count"] >= 1          # the test loop and the security loop
    assert summary["tests_failed"] == 3          # 17/20 on the first run
    assert summary["tests_passed"] >= 20
    assert summary["security_findings_count"] >= 1
    assert summary["human_interventions"] == 0   # everything was automatic

    decisions = memory_agent.query(pid)
    assert decisions and all(d["project_id"] == pid for d in decisions)

    gates = {g["gate"] for g in memory_agent.query_gate_results(pid)}
    assert {"plan", "tests", "security", "release"} <= gates


def test_only_real_human_approvals_count(memory_on):
    pid = _pid()
    rec = Recorder(pid)
    rec.approval(True, auto=True)
    assert metrics.get_summary(pid)["human_interventions"] == 0
    rec.approval(True, auto=False)
    assert metrics.get_summary(pid)["human_interventions"] == 1


def test_memory_errors_never_stop_the_pipeline(memory_on, stub_agents, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(memory_agent, "store_gate_result", boom)
    monkeypatch.setattr(metrics, "record_event", boom)
    monkeypatch.setattr(memory_agent, "store", boom)
    ctx = run_pipeline("task management SaaS", project_id=_pid(), auto_approve=True, demo_mode=True)
    assert ctx.status.value == "RELEASED"


def test_recording_can_be_switched_off(memory_on, stub_agents, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MEMORY", "off")
    pid = _pid()
    run_pipeline("task management SaaS", project_id=pid, auto_approve=True, demo_mode=True)
    assert metrics.get_summary(pid)["retry_count"] == 0
    assert memory_agent.query(pid) == []


def test_decisions_are_stored_with_the_running_project_id(memory_on):
    pid = _pid()
    plan = AgentResult(
        agent="plan_agent",
        status=AgentStatus.PASS,
        summary="ok",
        data={"decisions": [{
            "id": "DEC-999", "project_id": "some_other_project", "question": "Database?",
            "alternatives": ["PostgreSQL", "MongoDB"], "decision": "PostgreSQL",
            "reason": "relational", "source": "plan_agent", "timestamp": "2026-09-26T00:00:00Z",
        }, {
            "question": "No alternatives", "alternatives": [], "decision": "x", "reason": "y", "source": "s",
        }]},
        duration_seconds=0.1,
        timestamp="2026-09-26T00:00:00Z",
    )
    Recorder(pid).decisions(plan)
    stored = memory_agent.query(pid)
    assert len(stored) == 1 and stored[0]["project_id"] == pid


def test_gate_result_is_stored_as_plain_json(memory_on):
    pid = _pid()
    gate = GateResult(gate=GateName.TESTS, project_id=pid, verdict=GateVerdict.FAIL,
                      reason="17/20", timestamp="2026-09-26T00:00:00Z")
    Recorder(pid).gate(gate)
    stored = memory_agent.query_gate_results(pid)
    assert stored[0]["gate"] == "tests" and stored[0]["verdict"] == "FAIL"
    json.dumps(stored)  # must be serialisable
