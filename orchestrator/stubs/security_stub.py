"""
orchestrator/stubs/security_stub.py
Stub for the Security Agent (Haytam's agent).

Demo behaviour (configurable):
  - Call 1 → BLOCKED with 1 HIGH finding (broken_access_control)
  - Call 2+ → PASS, zero findings

The `fail_first` flag (default True) enables the security-fix loop demo.

Replace with: from security.security_agent import SecurityAgent
              register_agent("security", SecurityAgent())
"""

import time
from datetime import datetime, timezone

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


class SecurityStub(BaseAgent):
    """Owner: Haytam — replace with security/security_agent.py when ready."""

    def __init__(self, fail_first: bool = True) -> None:
        self._call_count = 0
        self.fail_first = fail_first

    def reset(self) -> None:
        self._call_count = 0

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        self._call_count += 1

        if self.fail_first and self._call_count == 1:
            return AgentResult(
                agent="security_agent",
                status=AgentStatus.FAIL,
                summary="[STUB] 1 HIGH finding. Pipeline BLOCKED.",
                data={
                    "verdict": "BLOCKED",
                    "counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
                    "findings": [
                        {
                            "id": "SEC-001",
                            "severity": "high",
                            "type": "broken_access_control",
                            "location": "backend/routers/tasks.py:54",
                            "description": "DELETE /tasks/{id} does not verify task ownership",
                            "recommended_fix": (
                                "Add: if task.owner_id != current_user.id: "
                                "raise HTTPException(status_code=403)"
                            ),
                        }
                    ],
                },
                duration_seconds=round(time.time() - start, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        return AgentResult(
            agent="security_agent",
            status=AgentStatus.PASS,
            summary="[STUB] No findings. Pipeline clear.",
            data={
                "verdict": "PASS",
                "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "findings": [],
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
