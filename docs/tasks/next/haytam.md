# Haytam: next tasks

**Branch:** `haytam/security`. **Folder:** `security/`.

## Status (reviewed)
**Nothing from you is on GitHub yet.** `security/gate.py`, `scanner.py`, `security_agent.py` and the security fixtures are still one-line placeholders. If you have work, **push it and open a Pull Request today, even if partial.** If you have nothing, start with task 2.

## Goal
Security is a real gate: the agent finds a real vulnerability, the gate blocks, the fix is applied, the gate passes.

## The demo file
`backend/demo_bug.py` has two planted problems:
1. A missing ownership check on DELETE (CWE-639): found by Manar's tests and fixed by her debug agent. **This is not yours.**
2. A **hard-coded secret** (CWE-798) that Manar is adding: this is **yours**. Ask Manar for the exact line.

## Tasks (in order)

1. **Push and PR** whatever you have.
2. **Fixtures** in `tests/fixtures/security_finding_HIGH.json` and `security_pass.json` (currently empty), following `SecurityFinding`: `id`, `severity` (`high`), `type` (`secrets_exposure`), `location` (`backend/demo_bug.py:<line>`), `description`, `recommended_fix`.
3. **Security agent** (`security/security_agent.py`, class extending `BaseAgent`) returning an `AgentResult` with `data`: `verdict` (`PASS` or `BLOCKED`), `counts` (critical, high, medium, low), `findings` (list of `SecurityFinding`). The gate blocks on critical or high.
4. **A real check.** Scan `backend/demo_bug.py` for hard-coded secrets (a simple regex on names such as `SECRET`, `KEY`, `PASSWORD`, `TOKEN` assigned to a string literal). You can add Bandit for extra findings. Bandit alone does not find missing ownership checks.
5. **Fix agent** (`security/fix_agent.py`): replace the hard-coded value with `os.environ.get("API_SECRET_KEY")`, then the agent rescans and returns `PASS`. Do not touch the ownership check.
6. **Thread safety:** the orchestrator runs tests and security in parallel. No shared files or global state.
7. **Register** as stages `security` and `fix`, keeping the stubs as a fallback if yours raises an error.
8. **Tests** in `tests/test_security_agent.py`: BLOCKED with the planted secret, PASS after the fix, gate blocks on high, gate passes with only low findings.
9. **Bob evidence:** fill `bob_sessions/haytam_security_session.md` (prompt, output, features used, screenshots).
10. **Demo:** a 20-second explanation of what was found, why it blocks the release, and how it was fixed automatically.

## Done when
The pipeline shows SECURITY blocked with your finding, then FIX, then SECURITY pass, with your real agents.

## Talk to
Manar (second bug, exact line), Leader (registration).
