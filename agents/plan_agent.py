"""
DevForge - Plan Agent
Research + Requirements + Architecture
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext


FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "plan_output.json"
)


class PlanAgent(BaseAgent):
    """Plan Agent that loads the saved Bob plan and adapts it to the project context."""

    def run(self, context: ProjectContext) -> AgentResult:
        """Run the Plan Agent for the current project."""

        started = time.perf_counter()
        try:
            with FIXTURE_PATH.open("r", encoding="utf-8") as file:
                data = json.load(file)

            # Use the idea from the running project context.
            data["data"]["idea"] = context.idea

            # Make every decision belong to the running project.
            for decision in data["data"].get("decisions", []):
                decision["project_id"] = context.project_id

            # Keep ADR decisions consistent with the same project id.
            for decision in data["data"].get("architecture", {}).get("adr", []):
                decision["project_id"] = context.project_id

            # The plan comes from a saved Bob Plan session. Report the real time of this call and the
            # current time, not the numbers stored in the fixture, so the metrics stay honest.
            data["data"]["source"] = "saved Bob Plan session (replayed)"
            data["duration_seconds"] = round(time.perf_counter() - started, 3)
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

            return AgentResult.model_validate(data)

        except FileNotFoundError:
            return AgentResult(
                agent="plan_agent",
                status=AgentStatus.ERROR,
                summary=f"Plan fixture not found: {FIXTURE_PATH}",
                data={},
                duration_seconds=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            return AgentResult(
                agent="plan_agent",
                status=AgentStatus.ERROR,
                summary=f"Invalid Plan Agent fixture: {error}",
                data={},
                duration_seconds=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )


def run(input: dict[str, Any]) -> AgentResult:
    """
    Backward-compatible function for existing tests.
    """
    context = ProjectContext(
        project_id=input.get("project_id", "proj_task_management"),
        idea=input.get("idea", "task-management SaaS for small teams"),
        created_at=input.get("created_at", "2026-09-26T00:00:00Z"),
    )

    return PlanAgent().run(context)