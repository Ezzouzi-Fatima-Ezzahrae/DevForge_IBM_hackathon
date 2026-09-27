# Haytam: next tasks

**Branch:** reset first: `git fetch origin && git checkout -B haytam/fix origin/main`. **Files:** `security/`, `tests/test_security_agent.py`.

## Done (merged)
Scanner that finds the planted ownership bug (HIGH, CWE-639) and also reports the hard-coded secret (rated LOW), connected to the orchestrator through `orchestrator/adapters/security_adapter.py`. The pipeline blocks on your real agent and passes after the Debugger's patch.

## To do (all in ONE Pull Request)

If the secret rule lands without the fix agent, the pipeline ends in FAILED, so they must ship together.

1. **Rate hard-coded secrets as HIGH** in `security/scanner.py` (names such as `SECRET`, `KEY`, `PASSWORD`, `TOKEN` assigned to a string literal, CWE-798). The demo line is `API_SECRET_KEY = "hardcoded-demo-secret"` in `backend/demo_bug.py`.
2. **Fix agent** in `security/fix_agent.py` (extends `BaseAgent`): replace the value with `os.environ.get("API_SECRET_KEY")`, return `AgentResult` (agent `fix_agent`, status PASS, `data` with `fixed_file` and `fix_applied`). Read and write UTF-8. Return `AgentResult(status=ERROR)` on failure, never crash. Do not touch the ownership check.
3. **Tests** in `tests/test_security_agent.py`: the scanner finds both problems, returns nothing on a clean file, the fix agent removes the secret and a rescan passes, a missing file returns ERROR.
4. Tell the Leader when it is ready; the Leader registers it as the `fix` stage in `agents_base.py`.
5. Clean the old fixture `tests/fixtures/security_finding_HIGH.json` (still points to `backend/routers/tasks.py`).
6. **Demo:** 20 seconds: what was found, why it blocks the release, how it was fixed.

## Done when
Security is BLOCKED by your real agent (two findings), your fix agent removes the secret, the Debugger fixes the ownership bug, then SECURITY passes and the run ends RELEASED (`python scripts/demo.py`).

## Talk to
Manar (the second bug line), Leader (registration).
