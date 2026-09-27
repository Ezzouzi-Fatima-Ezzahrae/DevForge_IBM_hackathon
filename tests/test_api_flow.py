"""End-to-end test of the dashboard API: create, start, approve twice, RELEASED.

Uses the stub agents so it never touches backend/demo_bug.py.
"""
import time

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from orchestrator import agents_base

STUB_ENV = ["DEVFORGE_PLAN_AGENT_MODE", "DEVFORGE_TEST_AGENT_MODE",
            "DEVFORGE_DEBUG_AGENT_MODE", "DEVFORGE_SECURITY_AGENT_MODE"]


@pytest.fixture()
def client(monkeypatch):
    for name in STUB_ENV:
        monkeypatch.setenv(name, "stub")
    agents_base._bootstrap_agents()
    yield TestClient(app)
    monkeypatch.undo()
    agents_base._bootstrap_agents()


def _wait(client, pid, predicate, seconds=30):
    end = time.time() + seconds
    last = None
    while time.time() < end:
        last = client.get(f"/projects/{pid}/status").json()
        if predicate(last):
            return last
        time.sleep(0.05)
    raise AssertionError(f"timeout, last status: {last and last.get('status')}")


def _run_to_first_approval(client):
    pid = client.post("/projects", json={"idea": "flow test"}).json()["project_id"]
    assert client.post(f"/projects/{pid}/start").json() == {"status": "started"}
    st = _wait(client, pid, lambda s: s["awaiting_approval"] is not None)
    return pid, st


def test_full_flow_reaches_released(client):
    pid, st = _run_to_first_approval(client)
    assert st["awaiting_approval"]["gate"] == "architecture"
    assert client.post(f"/projects/{pid}/approve", json={"gate": "architecture", "approved": True}).status_code == 200

    st = _wait(client, pid, lambda s: (s["awaiting_approval"] or {}).get("gate") == "release")
    names = [x["name"] for x in st["stages"]]
    assert names == ["plan", "build", "test", "debug", "security", "fix", "approval", "release"]
    assert client.post(f"/projects/{pid}/approve", json={"gate": "release", "approved": True}).status_code == 200

    st = _wait(client, pid, lambda s: s["status"] == "RELEASED" and not s["running"])
    assert st["stages"][-1]["state"] == "done"
    assert st["retries"]["test"] >= 1


def test_rejecting_the_architecture_fails_the_project(client):
    pid, _ = _run_to_first_approval(client)
    client.post(f"/projects/{pid}/approve", json={"gate": "architecture", "approved": False})
    st = _wait(client, pid, lambda s: s["status"] == "FAILED" and not s["running"])
    assert st["awaiting_approval"] is None


def test_approve_without_a_pending_request_is_409(client):
    pid = client.post("/projects", json={"idea": "x"}).json()["project_id"]
    r = client.post(f"/projects/{pid}/approve", json={"gate": "release", "approved": True})
    assert r.status_code == 409


def test_approving_the_wrong_gate_is_rejected(client):
    pid, st = _run_to_first_approval(client)
    assert st["awaiting_approval"]["gate"] == "architecture"
    r = client.post(f"/projects/{pid}/approve", json={"gate": "release", "approved": True})
    assert r.status_code == 409
    client.post(f"/projects/{pid}/approve", json={"gate": "architecture", "approved": False})
    _wait(client, pid, lambda s: not s["running"])
