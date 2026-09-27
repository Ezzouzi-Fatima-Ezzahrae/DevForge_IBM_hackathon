"""
orchestrator/agents_base.py
Common agent interface and registry.

Every agent (stub or real) must implement BaseAgent.run().
The registry maps each pipeline stage name to an agent instance.
Swap a stub for a real agent by replacing one registry entry.
"""

from __future__ import annotations

import abc
from typing import Callable

from orchestrator.contracts import AgentResult, ProjectContext


class BaseAgent(abc.ABC):
    """All agents implement this interface."""

    @abc.abstractmethod
    def run(self, context: ProjectContext) -> AgentResult:
        """Run the agent for the current pipeline context."""


# ─── Registry ─────────────────────────────────────────────────────────────────
# Maps stage name → agent instance.
# Import is deferred to avoid circular imports at module load time.
# Teammates: swap your stub by replacing the value here OR by calling
#   register_agent("stage_name", YourRealAgent())
# after importing this module.

_registry: dict[str, BaseAgent] = {}


def register_agent(stage: str, agent: BaseAgent) -> None:
    """Register (or replace) the agent for a given stage."""
    _registry[stage] = agent


def get_agent(stage: str) -> BaseAgent:
    """Return the agent for *stage*, raising KeyError if not registered."""
    if stage not in _registry:
        raise KeyError(f"No agent registered for stage '{stage}'")
    return _registry[stage]


def list_stages() -> list[str]:
    """Return the ordered list of registered stage names."""
    return list(_registry.keys())


def _real_or_stub(env_var: str, real_factory, stub_factory) -> BaseAgent:
    """Return the real agent, or the stub when it is switched off or cannot be loaded.

    Set the environment variable (for example DEVFORGE_PLAN_AGENT_MODE=stub) to force the stub.
    A problem while importing or creating the real agent must never break the orchestrator.
    """
    import os

    if os.environ.get(env_var, "real").strip().lower() == "stub":
        return stub_factory()
    try:
        return real_factory()
    except Exception as exc:  # noqa: BLE001 - fall back to the stub
        import traceback
        print(f"[DevForge] {env_var}: real agent failed to load ({type(exc).__name__}: {exc}); falling back to stub.", flush=True)
        traceback.print_exc()
        return stub_factory()


def _bootstrap_agents() -> None:
    """
    Populate the registry: every stage gets its real agent, with the stub as fallback.

    Stage            Real agent (owner)                       Switch to the stub
    plan             agents.plan_agent.PlanAgent (Fati)       DEVFORGE_PLAN_AGENT_MODE=stub
    test             agents.testing_agent (Manar)             DEVFORGE_TEST_AGENT_MODE=stub
    debug            agents.debug_agent (Manar)               DEVFORGE_DEBUG_AGENT_MODE=stub
    security         orchestrator.adapters.security_adapter   DEVFORGE_SECURITY_AGENT_MODE=stub
    fix              orchestrator.adapters.fix_adapter         DEVFORGE_FIX_AGENT_MODE=stub
    build            stub only for now
    """
    from orchestrator.stubs.builder_stub import BuilderStub
    from orchestrator.stubs.debug_stub import DebugStub
    from orchestrator.stubs.fix_stub import FixStub
    from orchestrator.stubs.plan_stub import PlanStub
    from orchestrator.stubs.security_stub import SecurityStub
    from orchestrator.stubs.tester_stub import TesterStub

    def real_plan():
        from agents.plan_agent import PlanAgent

        return PlanAgent()

    def real_test():
        from agents.testing_agent.agent import TestingAgent

        return TestingAgent()

    def real_debug():
        from agents.debug_agent.agent import DebugAgent

        return DebugAgent()

    def real_security():
        from orchestrator.adapters.security_adapter import SecurityAdapter

        return SecurityAdapter()

    def real_fix():
        from orchestrator.adapters.fix_adapter import FixAdapter

        return FixAdapter()

    register_agent("plan", _real_or_stub("DEVFORGE_PLAN_AGENT_MODE", real_plan, PlanStub))
    register_agent("build", BuilderStub())
    register_agent("test", _real_or_stub("DEVFORGE_TEST_AGENT_MODE", real_test, TesterStub))
    register_agent("debug", _real_or_stub("DEVFORGE_DEBUG_AGENT_MODE", real_debug, DebugStub))
    register_agent("security", _real_or_stub("DEVFORGE_SECURITY_AGENT_MODE", real_security, SecurityStub))
    register_agent("fix", _real_or_stub("DEVFORGE_FIX_AGENT_MODE", real_fix, FixStub))


# Kept for older code that imported the previous name.
_bootstrap_stubs = _bootstrap_agents

_bootstrap_agents()
