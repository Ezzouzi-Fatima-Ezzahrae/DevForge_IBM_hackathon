"""Testing Agent for the DevForge orchestrator."""

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext
import os

class TestingAgent:
    """Run the real pytest suite for the demo task backend."""

    def __init__(self, fail_first: bool = True) -> None:
        self.fail_first = fail_first

    def reset(self) -> None:
        """Keep the orchestrator interface compatible."""
        pass

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        if os.getenv("DEVFORGE_TEST_AGENT_MODE", "real") == "stub":
            from orchestrator.stubs.tester_stub import TesterStub
            return TesterStub(fail_first=True).run(context)

        project_root = Path(__file__).resolve().parents[2]
        test_file = project_root / "tests" / "test_demo_tasks.py"

        command = [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-q",
        ]

        completed = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        output = completed.stdout + completed.stderr

        passed = self._extract_count(output, "passed")
        failed = self._extract_count(output, "failed")
        total = passed + failed

        failures = self._extract_failures(output)

        status = AgentStatus.PASS if completed.returncode == 0 else AgentStatus.FAIL

        summary = (
            f"{passed}/{total} tests passed."
            if total
            else "pytest did not report test counts."
        )

        if failed:
            summary += f" {failed} tests failed."

        return AgentResult(
            agent="tester_agent",
            status=status,
            summary=summary,
            data={
                "total": total,
                "passed": passed,
                "failed": failed,
                "status": "PASS" if status == AgentStatus.PASS else "FAIL",
                "failures": failures,
                "pytest_command": "python -m pytest tests/test_demo_tasks.py -q",
                "pytest_returncode": completed.returncode,
                "pytest_output": output,
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _extract_count(output: str, word: str) -> int:
        """Extract a pytest count such as '17 passed' or '3 failed'."""
        import re

        match = re.search(rf"(\d+)\s+{word}", output)

        return int(match.group(1)) if match else 0

    @staticmethod
    def _extract_failures(output: str) -> list[dict[str, str]]:
        """Extract failed test names and their pytest failure messages."""
        import re

        failures: list[dict[str, str]] = []

        pattern = re.compile(
            r"FAILED\s+([^\s]+)\s+-\s+(.+)"
        )

        for match in pattern.finditer(output):
            failures.append(
                {
                    "test": match.group(1).split("::")[-1],
                    "error": match.group(2).strip(),
                }
            )

        return failures