# Manar: next tasks

**Branch:** `manar/testing`. **Folders:** `agents/testing_agent`, `agents/debug_agent`, `tests/`, and the file `backend/demo_bug.py` only.

## Status (reviewed)
Done and good: real testing agent (runs pytest on `tests/test_demo_tasks.py`), real debug agent (patches `backend/demo_bug.py` and reruns), restore script and pristine copy, an environment switch to the stub, filled Bob summaries. 17/20 then 20/20 is real.

## Tasks (in order)

1. **Open a Pull Request** into `main` if you have not yet.
2. **Second planted bug for the security agent.** Your debug agent already fixes the ownership bug, so the security agent would find nothing. Add a second, different vulnerability to `backend/demo_bug.py`, for example a hard-coded secret: `API_SECRET_KEY = "hardcoded-demo-secret"` used in the code (CWE-798). Do not change the 20 tests; they must still give 17/20 then 20/20. Update `tests/fixtures/demo_bug_original.py` and tell Haytam the exact line.
3. **Clean the tests.** Two of your three failing tests are identical (`test_delete_task_not_owner` and `test_delete_task_unauthorized_owner` both delete task 1), and several passing tests repeat each other. Replace the duplicates with different checks (for example: a non-owner cannot delete task 3, the task list is unchanged after a rejected delete, delete without a user, updating a task). Keep exactly 3 failing tests on the buggy version.
4. **Fallback on error, not only by environment variable.** If pytest cannot run (missing package or timeout), return `AgentResult(status=ERROR)` with a clear message, and add a `timeout` to the subprocess. Add a `requirements.txt` line for `fastapi` and `httpx` if the tests need them.
5. **Make the agents extend `BaseAgent`** (`from orchestrator.agents_base import BaseAgent`) for consistency, unless it causes an import cycle; if so tell the Leader.
6. **Regression after the security fix:** after Haytam's fix agent patches the secret, the tests must still be 20/20. Add a test for this (`tests/test_regression.py`).
7. **Escalation test:** `test_debug_loop_max_3_escalates`: if the debug agent fails 3 times, the pipeline ends in `FAILED`.
8. **Cleanup:** remove or use the old placeholders `agents/tester_agent.py`, `agents/debugger_agent.py`, `agents/prompts/tester.md`, `debugger.md`, and the empty fixtures.
9. **Demo:** be ready to explain the 17/20, root cause, patch and 20/20 in 30 seconds.

## Done when
Two runs in a row (with `python tests/restore_demo_bug.py` in between) both show 17/20, a real patch and 20/20, and the second planted bug is still present after the debug agent.

## Talk to
Haytam (second bug, same file), Leader (orchestrator changes), Ali (test results on the dashboard).
