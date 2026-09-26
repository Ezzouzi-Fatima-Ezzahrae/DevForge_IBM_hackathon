"""
orchestrator/stubs/debug_stub.py
Stub for the Debugger Agent (Manar's agent).
Always returns a successful fix — the Tester rerun will then PASS.
Replace with: from agents.debug_agent.agent import DebugAgent
              register_agent("debug", DebugAgent())
"""

import time
from datetime import datetime, timezone

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


class DebugStub(BaseAgent):
    """Owner: Manar — replace with agents/debug_agent/agent.py when ready."""

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        return AgentResult(
            agent="debug_agent",
            status=AgentStatus.PASS,
            summary="[STUB] Root cause found: missing ownership check on DELETE /tasks/{id}. Patch applied.",
            data={
                "root_cause": "DELETE /tasks/{id} does not verify task.owner_id == current_user.id",
                "fix_applied": "Added: if task.owner_id != current_user.id: raise HTTPException(403)",
                "fixed_file": "backend/routers/tasks.py",
                "rerun_result": {
                    "total": 20, "passed": 20, "failed": 0, "status": "PASS"
                },
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
