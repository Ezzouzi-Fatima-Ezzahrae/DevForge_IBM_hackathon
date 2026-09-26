"""Testing Agent for the DevForge orchestrator."""

import time
from datetime import datetime, timezone

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


class TestingAgent(BaseAgent):
    """Testing Agent compatible with the DevForge orchestrator.

    Demo behaviour:
    - First call: 17/20 tests fail.
    - Second and later calls: 20/20 tests pass.

    This keeps the current hackathon demo behaviour while using
    the official orchestrator AgentResult contract.
    """

    def __init__(self, fail_first: bool = True) -> None:
        self._call_count = 0
        self.fail_first = fail_first

    def reset(self) -> None:
        """Reset the test call counter between milestones."""
        self._call_count = 0

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        self._call_count += 1

        milestone_id = None
        if context.milestones:
            milestone_id = context.milestones[
                context.current_milestone_index
            ].id

        if self.fail_first and self._call_count == 1:
            return AgentResult(
                agent="tester_agent",
                status=AgentStatus.FAIL,
                summary="17/20 tests passed. 3 ownership-check failures.",
                data={
                    "total": 20,
                    "passed": 17,
                    "failed": 3,
                    "status": "FAIL",
                    "failures": [
                        {
                            "test": "test_delete_task_not_owner",
                            "error": "AssertionError: expected 403, got 200",
                        },
                        {
                            "test": "test_delete_task_other_user",
                            "error": "AssertionError: expected 403, got 200",
                        },
                        {
                            "test": "test_delete_task_unauthenticated",
                            "error": "AssertionError: expected 401, got 200",
                        },
                    ],
                    "coverage_percent": 72.0,
                    "milestone_id": milestone_id,
                },
                duration_seconds=round(time.time() - start, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        return AgentResult(
            agent="tester_agent",
            status=AgentStatus.PASS,
            summary="20/20 tests passed.",
            data={
                "total": 20,
                "passed": 20,
                "failed": 0,
                "status": "PASS",
                "failures": [],
                "coverage_percent": 85.0,
                "milestone_id": milestone_id,
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )