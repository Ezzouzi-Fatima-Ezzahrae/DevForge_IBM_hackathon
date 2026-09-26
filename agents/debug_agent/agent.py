"""Debug Agent — stub implementation that analyses test failures and applies fixes."""

import json
import os
from datetime import datetime

# Resolve fixture paths relative to this file so the agent works from any cwd.
_BASE = os.path.dirname(os.path.abspath(__file__))
_FIXTURES = os.path.join(_BASE, "..", "..", "tests", "fixtures")

_PASS_FIXTURE = os.path.join(_FIXTURES, "test_pass_20_20.json")

# Signature of the known ownership-check failure.
_OWNERSHIP_TEST = "test_delete_task_not_owner"
_OWNERSHIP_ERROR = "expected 403, got 200"


def _is_ownership_failure(test_result: dict) -> bool:
    """Return True when *test_result* matches the DELETE ownership failure."""
    failures = test_result.get("data", {}).get("failures", [])
    return any(
        f.get("test") == _OWNERSHIP_TEST and _OWNERSHIP_ERROR in f.get("error", "")
        for f in failures
    )


class DebugAgent:
    """Stub Debug Agent.

    Analyses a TestingAgent result, identifies the root cause, applies a
    targeted fix, and returns an AgentResult with rerun_result data.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, test_result: dict, code_files: list[str], logs: str) -> dict:
        """Analyse *test_result*, fix the issue, and return an AgentResult.

        Args:
            test_result: AgentResult dict produced by TestingAgent.
            code_files:  List of source-file paths belonging to the milestone.
            logs:        Raw log string captured during the test run.

        Returns:
            AgentResult dict with ``data`` shaped as::

                {
                    "root_cause":  str,
                    "fix_applied": str,
                    "fixed_file":  str,
                    "rerun_result": {
                        "total":   int,
                        "passed":  int,
                        "failed":  int,
                        "status":  "PASS" | "FAIL",
                    },
                }
        """
        start = datetime.utcnow()

        if _is_ownership_failure(test_result):
            data = _build_ownership_fix_data()
            status = "PASS"
            summary = (
                "Root cause identified: missing ownership check on DELETE /tasks/{id}. "
                "Fix applied — all 20 tests now pass."
            )
        else:
            data = _build_unknown_failure_data(test_result)
            status = "ERROR"
            summary = "Unrecognised failure pattern — no automated fix available."

        return {
            "agent": "debug_agent",
            "status": status,
            "summary": summary,
            "data": data,
            "duration_seconds": round(
                (datetime.utcnow() - start).total_seconds(), 4
            ),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_ownership_fix_data() -> dict:
    """Return data block for the known ownership-check fix."""
    with open(_PASS_FIXTURE, encoding="utf-8") as fh:
        pass_result: dict = json.load(fh)

    rerun = pass_result["data"]

    return {
        "root_cause": "DELETE /tasks/{id} does not check task ownership",
        "fix_applied": (
            "Added ownership check: "
            "if task.owner_id != current_user.id: raise 403"
        ),
        "fixed_file": "backend/routers/tasks.py",
        "rerun_result": {
            "total": rerun["total"],
            "passed": rerun["passed"],
            "failed": rerun["failed"],
            "status": rerun["status"],
        },
    }


def _build_unknown_failure_data(test_result: dict) -> dict:
    """Return a minimal data block when the failure pattern is unrecognised."""
    return {
        "root_cause": "Unknown — manual investigation required",
        "fix_applied": "None",
        "fixed_file": "",
        "rerun_result": {
            "total": test_result.get("data", {}).get("total", 0),
            "passed": test_result.get("data", {}).get("passed", 0),
            "failed": test_result.get("data", {}).get("failed", 0),
            "status": "FAIL",
        },
    }
