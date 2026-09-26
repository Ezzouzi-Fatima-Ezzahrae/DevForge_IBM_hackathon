"""
orchestrator/stubs/fix_stub.py
Stub for the Fix step (Builder applying a security patch — Haytam + Ali).
Always returns success. After this, security_stub's second call returns PASS.
Replace with real fix logic when Haytam wires the patch loop.
"""

import time
from datetime import datetime, timezone

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


class FixStub(BaseAgent):
    """Security fix stub — patches the finding and signals ready for rescan."""

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        return AgentResult(
            agent="fix_agent",
            status=AgentStatus.PASS,
            summary="[STUB] Security patch applied to backend/routers/tasks.py:54",
            data={
                "patched_file": "backend/routers/tasks.py",
                "finding_id": "SEC-001",
                "patch": "Added ownership check before DELETE operation",
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
