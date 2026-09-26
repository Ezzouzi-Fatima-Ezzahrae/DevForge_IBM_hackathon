"""
orchestrator/stubs/plan_stub.py
Stub for the Plan Agent (Fati's agent: research + requirements + architecture).
Returns a fixed valid AgentResult with 6 user stories and 1 ADR.
Replace with: from agents.plan_agent import PlanAgent; register_agent("plan", PlanAgent())
"""

import time
from datetime import datetime, timezone

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


class PlanStub(BaseAgent):
    """Owner: Fati — replace with agents/plan_agent.py when ready."""

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        return AgentResult(
            agent="plan_agent",
            status=AgentStatus.PASS,
            summary="[STUB] Generated 6 user stories, PostgreSQL ADR, and API list for task-management SaaS",
            data={
                "requirements": [
                    {"id": "REQ-001", "type": "functional",
                     "user_story": "As a user I can register and log in",
                     "acceptance_criteria": ["JWT returned on login"],
                     "priority": "must_have"},
                    {"id": "REQ-002", "type": "functional",
                     "user_story": "As a user I can create a task with title and due date",
                     "acceptance_criteria": ["Task appears in my list after creation"],
                     "priority": "must_have"},
                    {"id": "REQ-003", "type": "functional",
                     "user_story": "As a user I can list my tasks",
                     "acceptance_criteria": ["Only my tasks are returned"],
                     "priority": "must_have"},
                    {"id": "REQ-004", "type": "functional",
                     "user_story": "As a user I can update a task status",
                     "acceptance_criteria": ["Status is persisted"],
                     "priority": "must_have"},
                    {"id": "REQ-005", "type": "functional",
                     "user_story": "As a user I can delete only my own tasks",
                     "acceptance_criteria": ["Other users' tasks return 403"],
                     "priority": "must_have"},
                    {"id": "REQ-006", "type": "non_functional",
                     "user_story": "As an operator the app starts with docker-compose up",
                     "acceptance_criteria": ["Starts in under 30 s"],
                     "priority": "should_have"},
                ],
                "architecture": {
                    "stack": "Next.js + FastAPI + PostgreSQL + Docker",
                    "adr": [{"id": "ADR-001",
                              "decision": "PostgreSQL",
                              "reason": "Relational data with ACID transactions required",
                              "alternatives": ["MongoDB", "SQLite"]}],
                },
                "decisions": [
                    {"id": "DEC-001",
                     "project_id": context.project_id,
                     "question": "Which database?",
                     "alternatives": ["PostgreSQL", "MongoDB"],
                     "decision": "PostgreSQL",
                     "reason": "Relational data, ACID transactions required",
                     "source": "plan_agent",
                     "timestamp": datetime.now(timezone.utc).isoformat()}
                ],
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
