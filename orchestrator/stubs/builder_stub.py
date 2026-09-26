"""
orchestrator/stubs/builder_stub.py
Stub for the Builder Agent (Ali's agent).
Returns a fixed list of generated files for Milestone 1.
Replace with: from agents.builder_agent import BuilderAgent; register_agent("build", BuilderAgent())
"""

import time
from datetime import datetime, timezone

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


class BuilderStub(BaseAgent):
    """Owner: Ali — replace with agents/builder_agent.py when ready."""

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        ms_index = context.current_milestone_index
        return AgentResult(
            agent="builder_agent",
            status=AgentStatus.PASS,
            summary=f"[STUB] Generated code for milestone {ms_index + 1}: Task CRUD API",
            data={
                "milestone_id": f"ms_{ms_index + 1:03d}",
                "files_generated": [
                    "backend/routers/tasks.py",
                    "backend/models/task.py",
                    "backend/schemas/task.py",
                ],
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
