"""Debug Agent for the DevForge orchestrator."""

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext
import os

class DebugAgent:
    """Identify and apply the ownership-check fix."""

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        if os.getenv("DEVFORGE_DEBUG_AGENT_MODE", "real") == "stub":
            from orchestrator.stubs.debug_stub import DebugStub
            return DebugStub().run(context)


        project_root = Path(__file__).resolve().parents[2]
        bug_file = project_root / "backend" / "demo_bug.py"

        try:
            source = bug_file.read_text()

            old_block = """    current_user = get_current_user()

    # BUG: no ownership check — any user can delete any task
    del tasks[tasks.index(task)]
"""

            new_block = """    current_user = get_current_user()

    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    del tasks[tasks.index(task)]
"""

            if old_block in source:
                bug_file.write_text(source.replace(old_block, new_block))
                fix_applied = True
            elif "if task.owner_id != current_user.id:" in source:
                fix_applied = False
            else:
                raise RuntimeError("Ownership-check bug pattern not found.")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/test_demo_tasks.py",
                    "-q",
                ],
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            output = result.stdout + result.stderr

            passed = self._extract_count(output, "passed")
            failed = self._extract_count(output, "failed")
            total = passed + failed

            status = (
                AgentStatus.PASS
                if result.returncode == 0
                else AgentStatus.FAIL
            )

            return AgentResult(
                agent="debug_agent",
                status=status,
                summary=f"Ownership fix applied. Tests: {passed}/{total} passed.",
                data={
                    "root_cause": "Missing ownership check in DELETE /tasks/{task_id}.",
                    "fix_applied": fix_applied,
                    "fixed_file": "backend/demo_bug.py",
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "pytest_returncode": result.returncode,
                    "pytest_output": output,
                },
                duration_seconds=round(time.time() - start, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as exc:
            return AgentResult(
                agent="debug_agent",
                status=AgentStatus.ERROR,
                summary=f"Debug agent failed: {exc}",
                data={
                    "root_cause": "Debug agent execution error.",
                    "fix_applied": False,
                    "fixed_file": "",
                    "error": str(exc),
                },
                duration_seconds=round(time.time() - start, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    @staticmethod
    def _extract_count(output: str, word: str) -> int:
        import re

        match = re.search(rf"(\d+)\s+{word}", output)
        return int(match.group(1)) if match else 0