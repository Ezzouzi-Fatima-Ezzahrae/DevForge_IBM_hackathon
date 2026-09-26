# Haytam: next tasks

**Branch:** `haytam/security`. **Folder:** `security/` and `tests/test_security_agent.py` only.

## Status (reviewed)
Your scanner works: it really detects the planted ownership bug in `backend/demo_bug.py` (HIGH, CWE-639), and it passes on the fixed file. The Leader took your `security/` folder, your prompt, your fixtures and your Bob summary, and connected them to the orchestrator with an adapter (`orchestrator/adapters/security_adapter.py`). The pipeline now runs with your real security agent (tests fail 17/20 and security BLOCKED in the same round, then pass after the debug patch).

**Not taken from your branch** (they conflict with the shared code): your changes to `orchestrator/`, `memory/schemas.py`, `docs/agent_contracts.md`, `backend/`, and your orchestrator tests. Your security models now live in `security/schemas.py`. Do not merge your old PR; close it.

## First: update your branch
```
git checkout haytam/security
git fetch origin
git reset --hard origin/main      # ONLY after the Leader's integration PR is merged into main
```
(This discards your old orchestrator edits on purpose. Keep a copy of anything you still want.)

## Tasks (in order, inside `security/` and `tests/` only)

1. **Rate hard-coded secrets as HIGH.** Bandit reports them as LOW, so the gate ignores them. Add a custom rule in `security/scanner.py` for names such as `SECRET`, `KEY`, `PASSWORD`, `TOKEN` assigned to a string literal (CWE-798). Manar is adding `API_SECRET_KEY = "hardcoded-demo-secret"` to `backend/demo_bug.py`.
2. **Fix agent** (`security/fix_agent.py`, extending `BaseAgent` from `orchestrator.agents_base`): replace the hard-coded value with `os.environ.get("API_SECRET_KEY")`, return an `AgentResult` (agent `fix_agent`, status PASS, `data` with `fixed_file` and `fix_applied`). Read and write files as UTF-8. Never crash: return `AgentResult(status=ERROR)` on failure. Do not touch the ownership check (the debug agent fixes that).
3. **Register it** (the Leader does this in `agents_base.py` when your agent is ready; tell the Leader).
4. **Tests** in `tests/test_security_agent.py`: the scanner finds the ownership bug, finds the hard-coded secret as HIGH, returns nothing on a clean file; the fix agent removes the secret and a rescan passes; a missing file returns ERROR, never PASS.
5. **Clean the demo fixtures.** `tests/fixtures/security_finding_HIGH.json` still points to `backend/routers/tasks.py:54` with a 2025 timestamp; update it to `backend/demo_bug.py` and today's format, or delete demo mode if unused.
6. Replace `datetime.utcnow()` if you use it (use timezone-aware times).
7. **Bob evidence:** your summary exists; add your screenshots and name the Bob features used.
8. **Demo:** a 20-second explanation of what was found, why it blocks the release, and how it was fixed.

## Done when
The pipeline shows SECURITY blocked by your real agent (ownership bug and hard-coded secret), then the fix agent removes the secret, then SECURITY passes.

## Demo role
Haytam speaks about the security step (about 35 seconds): the finding, why it blocks the release, the fix, the rescan. See `docs/DEMO_PLAN.md`. Feature freeze is at hour 40; after that only fix bugs that break a rehearsal.

## Talk to
Manar (second bug line), Leader (registration, adapter).
