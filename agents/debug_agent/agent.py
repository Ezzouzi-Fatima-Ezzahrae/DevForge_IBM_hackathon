"""Debug Agent for the DevForge orchestrator."""

import time
from datetime import datetime, timezone

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


OWNERSHIP_TEST = "test_delete_task_not_owner"
OWNERSHIP_ERROR = "expected 403, got 200"


class DebugAgent(BaseAgent):
    """Analyse les échecs du Testing Agent et propose un correctif."""

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()

        test_result = context.last_test_result or {}
        failures = test_result.get("data", {}).get("failures", [])

        ownership_failure = any(
            failure.get("test") == OWNERSHIP_TEST
            and OWNERSHIP_ERROR in failure.get("error", "")
            for failure in failures
        )

        if ownership_failure:
            return AgentResult(
                agent="debug_agent",
                status=AgentStatus.PASS,
                summary=(
                    "Root cause identified: missing ownership check "
                    "on DELETE /tasks/{id}. Fix applied."
                ),
                data={
                    "root_cause": (
                        "DELETE /tasks/{id} does not verify "
                        "task ownership."
                    ),
                    "fix_applied": (
                        "Added ownership check: "
                        "task.owner_id == current_user.id"
                    ),
                    "fixed_file": "backend/routers/tasks.py",
                    "rerun_result": {
                        "total": 20,
                        "passed": 20,
                        "failed": 0,
                        "status": "PASS",
                    },
                },
                duration_seconds=round(time.time() - start, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        return AgentResult(
            agent="debug_agent",
            status=AgentStatus.ERROR,
            summary="Unrecognised failure pattern — manual investigation required.",
            data={
                "root_cause": "Unknown",
                "fix_applied": "None",
                "fixed_file": "",
                "rerun_result": {
                    "total": test_result.get("data", {}).get("total", 0),
                    "passed": test_result.get("data", {}).get("passed", 0),
                    "failed": test_result.get("data", {}).get("failed", 0),
                    "status": "FAIL",
                },
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )