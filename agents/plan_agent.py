"""
DevForge - Plan Agent
Research + Requirements + Architecture

H6-H10:
Loads the demo plan from fixtures/plan_output.json
and returns it as the canonical AgentResult.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.contracts import AgentResult


FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "plan_output.json"
)


def run(input: dict[str, Any]) -> AgentResult:
    """
    Run the Plan Agent stub.

    The current H6-H10 implementation loads the demo
    plan from fixtures/plan_output.json.
    """

    with FIXTURE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return AgentResult.model_validate(data)
