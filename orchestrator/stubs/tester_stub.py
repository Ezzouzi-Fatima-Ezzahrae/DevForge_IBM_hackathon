"""
orchestrator/stubs/tester_stub.py
Stub for the Testing Agent (Manar's agent).

Demo behaviour (configurable):
  - Call 1 → 17/20 FAIL  (simulates the planted ownership-check bug)
  - Call 2+ → 20/20 PASS (simulates post-debug rerun)

The `fail_first` flag (default True) enables the demo loop.
Set to False for a straight PASS if you don't need the debug loop.

Replace with: from agents.testing_agent.agent import TestingAgent
              register_agent("test", TestingAgent())
"""

import time
from datetime import datetime, timezone

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


class TesterStub(BaseAgent):
    """Owner: Manar — replace with agents/testing_agent/agent.py when ready."""

    def __init__(self, fail_first: bool = True) -> None:
        self._call_count = 0
        self.fail_first = fail_first

    def reset(self) -> None:
        """Reset call counter (call between milestones in tests)."""
        self._call_count = 0

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        self._call_count += 1
        ms_id = f"ms_{context.current_milestone_index + 1:03d}"

        if self.fail_first and self._call_count == 1:
            return AgentResult(
                agent="tester_agent",
                status=AgentStatus.FAIL,
                summary="[STUB] 17/20 tests passed. 3 ownership-check failures.",
                data={
                    "total": 20, "passed": 17, "failed": 3,
                    "status": "FAIL",
                    "failures": [
                        {"test": "test_delete_task_not_owner",
                         "error": "AssertionError: expected 403, got 200"},
                        {"test": "test_delete_task_other_user",
                         "error": "AssertionError: expected 403, got 200"},
                        {"test": "test_delete_task_unauthenticated",
                         "error": "AssertionError: expected 401, got 200"},
                    ],
                    "coverage_percent": 72.0,
                    "milestone_id": ms_id,
                },
                duration_seconds=round(time.time() - start, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        return AgentResult(
            agent="tester_agent",
            status=AgentStatus.PASS,
            summary="[STUB] 20/20 tests passed.",
            data={
                "total": 20, "passed": 20, "failed": 0,
                "status": "PASS",
                "failures": [],
                "coverage_percent": 85.0,
                "milestone_id": ms_id,
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
