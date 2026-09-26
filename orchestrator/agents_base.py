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


def _bootstrap_stubs() -> None:
    """
    Populate the registry with stubs on first import.
    Real agents can override entries after this runs.
    """

  

    from orchestrator.stubs.plan_stub import PlanStub
    from orchestrator.stubs.builder_stub import BuilderStub

    from agents.testing_agent.agent import TestingAgent
    from agents.debug_agent.agent import DebugAgent

    from orchestrator.stubs.security_stub import SecurityStub
    from orchestrator.stubs.fix_stub import FixStub

    register_agent("plan", PlanStub())
    register_agent("build", BuilderStub())
    register_agent("test", TestingAgent())
    register_agent("debug", DebugAgent())
    # Real security agent (Haytam), with the stub as fallback if it cannot be loaded.
    # Set DEVFORGE_SECURITY_AGENT_MODE=stub to force the stub.
    import os
    security_agent: BaseAgent = SecurityStub()
    if os.environ.get("DEVFORGE_SECURITY_AGENT_MODE", "real") != "stub":
        try:
            from orchestrator.adapters.security_adapter import SecurityAdapter
            security_agent = SecurityAdapter()
        except Exception:  # noqa: BLE001 - fall back to the stub
            security_agent = SecurityStub()
    register_agent("security", security_agent)
    register_agent("fix", FixStub())


_bootstrap_stubs()
