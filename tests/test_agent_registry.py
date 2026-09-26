"""The orchestrator registers real agents and falls back to the stubs when needed."""
import sys

import pytest

from orchestrator import agents_base
from orchestrator.stubs.debug_stub import DebugStub
from orchestrator.stubs.plan_stub import PlanStub
from orchestrator.stubs.security_stub import SecurityStub
from orchestrator.stubs.tester_stub import TesterStub


@pytest.fixture(autouse=True)
def restore_registry():
    saved = dict(agents_base._registry)
    yield
    agents_base._registry.clear()
    agents_base._registry.update(saved)


def test_default_registry_uses_the_real_plan_agent():
    agents_base._bootstrap_agents()
    assert agents_base.get_agent("plan").__class__.__name__ == "PlanAgent"


@pytest.mark.parametrize(
    "env_var, stage, stub_class",
    [
        ("DEVFORGE_PLAN_AGENT_MODE", "plan", PlanStub),
        ("DEVFORGE_TEST_AGENT_MODE", "test", TesterStub),
        ("DEVFORGE_DEBUG_AGENT_MODE", "debug", DebugStub),
        ("DEVFORGE_SECURITY_AGENT_MODE", "security", SecurityStub),
    ],
)
def test_environment_variable_switches_a_stage_to_its_stub(monkeypatch, env_var, stage, stub_class):
    monkeypatch.setenv(env_var, "stub")
    agents_base._bootstrap_agents()
    assert isinstance(agents_base.get_agent(stage), stub_class)


def test_a_broken_real_agent_falls_back_to_the_stub(monkeypatch):
    # Importing agents.plan_agent now raises ImportError.
    monkeypatch.setitem(sys.modules, "agents.plan_agent", None)
    agents_base._bootstrap_agents()
    assert isinstance(agents_base.get_agent("plan"), PlanStub)
