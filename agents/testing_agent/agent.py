"""Testing Agent — stub implementation returning pre-recorded fixtures."""

import json
import os
from datetime import datetime

# Resolve fixture paths relative to this file's location so the agent works
# regardless of the working directory.
_BASE = os.path.dirname(os.path.abspath(__file__))
_FIXTURES = os.path.join(_BASE, "..", "..", "tests", "fixtures")

_FAIL_FIXTURE = os.path.join(_FIXTURES, "test_fail_17_20.json")
_PASS_FIXTURE = os.path.join(_FIXTURES, "test_pass_20_20.json")


class TestingAgent:
    """Stub Testing Agent.

    First call to ``run`` returns the 17/20 FAIL fixture.
    Second (and subsequent) calls return the 20/20 PASS fixture.
    """

    def __init__(self) -> None:
        self._call_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, milestone: dict, code_files: list[str]) -> dict:
        """Execute (stub) tests for *milestone* and return an AgentResult.

        Args:
            milestone: Milestone descriptor dict from the orchestrator.
            code_files: List of source-file paths belonging to the milestone.

        Returns:
            AgentResult dict with ``data`` shaped as::

                {
                    "total": int,
                    "passed": int,
                    "failed": int,
                    "status": "PASS" | "FAIL",
                    "failures": [{"test": str, "error": str}],
                    "coverage_percent": float,
                }
        """
        start = datetime.utcnow()
        self._call_count += 1

        fixture_path = _FAIL_FIXTURE if self._call_count == 1 else _PASS_FIXTURE

        with open(fixture_path, encoding="utf-8") as fh:
            result: dict = json.load(fh)

        # Stamp the canonical agent identifier from the contract.
        result["agent"] = "tester_agent"

        # Refresh the timestamp to reflect actual execution time.
        result["timestamp"] = datetime.utcnow().isoformat() + "Z"
        result["duration_seconds"] = round(
            (datetime.utcnow() - start).total_seconds(), 4
        )

        return result
