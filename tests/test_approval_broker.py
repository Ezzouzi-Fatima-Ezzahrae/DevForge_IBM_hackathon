"""Tests for orchestrator/approval_broker.py and the approval_fn hook in run_pipeline."""
import threading
import time

import pytest

from orchestrator import agents_base
from orchestrator.approval_broker import ApprovalBroker, make_approval_fn
from orchestrator.contracts import ProjectContext, ProjectStatus
from orchestrator.runner import run_pipeline

STUB_ENV = [
    "DEVFORGE_PLAN_AGENT_MODE",
    "DEVFORGE_TEST_AGENT_MODE",
    "DEVFORGE_DEBUG_AGENT_MODE",
    "DEVFORGE_SECURITY_AGENT_MODE",
]


@pytest.fixture()
def stub_agents(monkeypatch):
    """Use the stubs so these tests never touch backend/demo_bug.py."""
    for name in STUB_ENV:
        monkeypatch.setenv(name, "stub")
    agents_base._bootstrap_agents()
    yield
    monkeypatch.undo()
    agents_base._bootstrap_agents()


def _ctx(pid="broker_t"):
    return ProjectContext(project_id=pid, idea="idea", status=ProjectStatus.IDLE, created_at="now")


def _wait_pending(b, pid, seconds=5.0):
    end = time.time() + seconds
    while time.time() < end:
        p = b.pending(pid)
        if p:
            return p
        time.sleep(0.01)
    return None


def _ask_in_thread(b, ctx, timeout=5.0):
    out = {}

    def target():
        out["v"] = b.request(ctx, [], "Approve?", timeout)

    t = threading.Thread(target=target)
    t.start()
    return t, out


def test_nothing_pending_by_default():
    b = ApprovalBroker()
    assert b.pending("x") is None
    assert b.resolve("x", True) is False


def test_approve_unblocks_request():
    b = ApprovalBroker()
    t, out = _ask_in_thread(b, _ctx())
    p = _wait_pending(b, "broker_t")
    assert p and p["prompt"] == "Approve?" and p["idea"] == "idea"
    assert b.resolve("broker_t", True) is True
    t.join(5)
    assert out["v"] is True
    assert b.pending("broker_t") is None


def test_reject_returns_false():
    b = ApprovalBroker()
    t, out = _ask_in_thread(b, _ctx())
    _wait_pending(b, "broker_t")
    b.resolve("broker_t", False)
    t.join(5)
    assert out["v"] is False


def test_timeout_is_a_rejection():
    b = ApprovalBroker()
    assert b.request(_ctx(), [], "Approve?", timeout=0.05) is False
    assert b.pending("broker_t") is None


def test_cancel_rejects():
    b = ApprovalBroker()
    t, out = _ask_in_thread(b, _ctx())
    _wait_pending(b, "broker_t")
    assert b.cancel("broker_t") is True
    t.join(5)
    assert out["v"] is False


def test_auto_approve_flag_skips_waiting():
    fn = make_approval_fn(target=ApprovalBroker(), timeout=0.05)
    assert fn(_ctx(), [], "x", auto_approve=True) is True


def test_full_pipeline_released_through_broker(stub_agents):
    b = ApprovalBroker()
    fn = make_approval_fn(target=b, timeout=20)
    pid = "broker_pipe_ok"
    result = {}

    t = threading.Thread(
        target=lambda: result.update(
            ctx=run_pipeline("idea", project_id=pid, approval_fn=fn, demo_mode=True)
        )
    )
    t.start()
    seen = []
    for _ in range(2):  # architecture, then release
        p = _wait_pending(b, pid, 20)
        assert p is not None, "pipeline never asked for approval"
        seen.append(p["prompt"])
        b.resolve(pid, True)
        time.sleep(0.05)
    t.join(30)
    assert not t.is_alive()
    assert result["ctx"].status == ProjectStatus.RELEASED
    assert len(seen) == 2 and seen[0] != seen[1]


def test_pipeline_rejected_at_architecture(stub_agents):
    b = ApprovalBroker()
    fn = make_approval_fn(target=b, timeout=20)
    pid = "broker_pipe_no"
    result = {}
    t = threading.Thread(
        target=lambda: result.update(ctx=run_pipeline("idea", project_id=pid, approval_fn=fn))
    )
    t.start()
    assert _wait_pending(b, pid, 20) is not None
    b.resolve(pid, False)
    t.join(30)
    assert result["ctx"].status == ProjectStatus.FAILED
    assert result["ctx"].human_approved_arch is not True


def test_pipeline_timeout_rejects_release(stub_agents):
    """No answer at all -> the pipeline must not release."""
    fn = make_approval_fn(target=ApprovalBroker(), timeout=0.2)
    ctx = run_pipeline("idea", project_id="broker_pipe_timeout", approval_fn=fn)
    assert ctx.status != ProjectStatus.RELEASED
