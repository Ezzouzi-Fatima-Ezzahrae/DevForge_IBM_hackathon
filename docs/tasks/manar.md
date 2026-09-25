# Manar — Testing and Debugging Lead

## Role
Testing and debugging lead. Prove that generated code actually works.

## Branch and Folders
- **Branch:** `manar/testing`
- **Folders:** `agents/testing_agent/`, `agents/debug_agent/`, `tests/`

---

## Objective
Build the Testing Agent and the Debugger Agent. Together they form the automated quality loop: generate tests → run them → find failures → fix them → rerun → all pass.

---

## Context
DevForge orchestrates: **Idea → Research → Requirements → Architecture → Milestones → Build → Test → Debug → Security → Human Approval → Release**.
Your agents own the Test and Debug stages. Testing runs immediately after each milestone is built. If tests fail, the Debugger runs. After a fix, the Tester reruns. The Security Agent (Haytam) runs only after tests pass.
Demo app: a simple task-management SaaS (FastAPI backend). Stack: FastAPI, PostgreSQL, pytest. Do not expand the stack.

Every agent returns:
```json
{ "agent": "...", "status": "PASS | FAIL | ERROR", "summary": "...", "data": {}, "duration_seconds": 0, "timestamp": "..." }
```

---

## Deliverables

- [ ] **Testing Agent** (`agents/testing_agent/agent.py`)
  - Input: `{ "milestone": {...}, "code_files": ["path/to/file.py", ...] }`
  - Generates tests for the milestone, runs them with pytest, analyzes failures.
  - Output `data` field:
    ```json
    {
      "total": 20, "passed": 17, "failed": 3,
      "status": "PASS | FAIL",
      "failures": [{ "test": "test_delete_task_not_owner", "error": "AssertionError: expected 403, got 200" }],
      "coverage_percent": 72
    }
    ```
  - Gate rule: **`PASS` only when passed == total (100%)**. Anything less is `FAIL`.

- [ ] **Debugger Agent** (`agents/debug_agent/agent.py`)
  - Input: failing `TestResult` data + code files + logs
  - Analyzes failure, identifies root cause, applies a targeted fix, reruns tests.
  - Output `data` field:
    ```json
    {
      "root_cause": "DELETE /tasks/{id} does not check task ownership",
      "fix_applied": "Added ownership check: if task.owner_id != current_user.id: raise 403",
      "fixed_file": "backend/routers/tasks.py",
      "rerun_result": { "total": 20, "passed": 20, "failed": 0, "status": "PASS" }
    }
    ```

- [ ] **Regression mechanism:** when a milestone is retested, run new tests AND all previous milestone tests. (Example: 8 new + 52 regression = 60/60 PASS.)

- [ ] **Demo fixtures:**
  - `tests/fixtures/test_fail_17_20.json` — pre-recorded test result: 17/20, 3 failures on the ownership check.
  - `tests/fixtures/test_pass_20_20.json` — pre-recorded test result: 20/20, all pass.
  - A small demo FastAPI file with **one intentional bug**: the DELETE /tasks/{id} endpoint has no ownership check.

- [ ] **Bob evidence:** `bob_sessions/manar_task01_testing_agent.png` and `bob_sessions/manar_task02_debug_agent.png`.

---

## Dependencies

| Depends on | What you need |
|---|---|
| **Leader** | Gate threshold (100% pass required); max debug retry limit (3 attempts before human escalation) |
| **Haytam** | Agree on shared `PASS/FAIL/FINDING/SEVERITY/FIX/RETEST` format before hour 4. Tests must pass before security runs. |
| **Ali** | `GET /tests` endpoint must match your TestResult data shape exactly |

---

## Bob Task
Use **Bob Agent mode** to build both agents.
1. Run the prompt below for the Testing Agent.
2. Screenshot → `bob_sessions/manar_task01_testing_agent.png`.
3. Run a second session for the Debugger Agent.
4. Screenshot → `bob_sessions/manar_task02_debug_agent.png`.

---

## Definition of Done
- [ ] Testing Agent runs and produces valid `AgentResult` JSON (can use the fixture files as output for now).
- [ ] Debugger Agent runs on the `test_fail_17_20.json` fixture and produces a `rerun_result` with `passed: 20`.
- [ ] Both fixture files are committed in `tests/fixtures/`.
- [ ] Demo bug file exists and the failing test is reproducible.
- [ ] Both Bob session screenshots saved in `bob_sessions/`.

---

## Deadline — First Sync (~hour 4)
Have both agent stubs returning valid JSON using the fixture files. The intentional bug must exist. Share your screen and confirm the shared result format with Haytam.

---

## Bob Prompt

```
You are an expert Python QA engineer and test automation specialist.

CONTEXT
Project: DevForge — an AI Software Development Lifecycle Orchestrator.
You are building the Testing Agent and the Debugger Agent for DevForge.
The agents test a FastAPI + PostgreSQL backend milestone.
Demo app being tested: a simple task-management SaaS (FastAPI backend).
Stack: Python 3.11, FastAPI, PostgreSQL, pytest. Do not add other testing tools.

AGENT RESULT SHAPE (both agents must return this):
{ "agent": "...", "status": "PASS | FAIL | ERROR", "summary": "...",
  "data": {}, "duration_seconds": 0, "timestamp": "..." }

TASK
1. Create agents/testing_agent/agent.py
   Class: TestingAgent
   Method: run(milestone: dict, code_files: list[str]) -> dict
   Returns AgentResult where data contains:
   { "total": int, "passed": int, "failed": int, "status": "PASS | FAIL",
     "failures": [{"test": str, "error": str}], "coverage_percent": float }
   Gate rule: status is PASS only when passed == total.
   For now, return the contents of tests/fixtures/test_fail_17_20.json on the first call
   and tests/fixtures/test_pass_20_20.json on the second call (stub behaviour).

2. Create agents/debug_agent/agent.py
   Class: DebugAgent
   Method: run(test_result: dict, code_files: list[str], logs: str) -> dict
   Returns AgentResult where data contains:
   { "root_cause": str, "fix_applied": str, "fixed_file": str,
     "rerun_result": { "total": int, "passed": int, "failed": int, "status": str } }
   For now, return a hard-coded fix for the ownership bug (stub behaviour).

3. Create tests/fixtures/test_fail_17_20.json
   A complete AgentResult for the testing_agent with 17/20 passed, 3 failures
   all on "test_delete_task_not_owner", error "AssertionError: expected 403, got 200".

4. Create tests/fixtures/test_pass_20_20.json
   A complete AgentResult for the testing_agent with 20/20 passed, 0 failures.

5. Create a demo file backend/demo_bug.py — a minimal FastAPI router for /tasks
   with one intentional bug: DELETE /tasks/{id} has no ownership check.
   Add a comment: # BUG: no ownership check — any user can delete any task

6. Create agents/testing_agent/__init__.py and agents/debug_agent/__init__.py.

CONSTRAINTS
- Pure Python 3.11, no real pytest execution yet (stubs only).
- Use datetime.utcnow().isoformat() + "Z" for timestamps.
- Keep each file under 80 lines.

OUTPUT FORMAT
File tree first, then each file in full.
```
