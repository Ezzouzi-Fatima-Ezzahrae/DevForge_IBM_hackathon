# Next tasks (round 2)

Each person has a file here with what to do next. Read `docs/STATUS.md` first.

| Person | File | Main goal |
|---|---|---|
| Ali | `ali.md` | Backend API that runs the orchestrator, then the dashboard |
| Fati | `fati.md` | Open your Pull Request, plug the real plan agent in, decisions and sources |
| Haytam | `haytam.md` | Security agent and fix agent that work on `backend/demo_bug.py` |
| Manar | `manar.md` | Make the testing and debug agents real, restore script, regression |
| Safa | `safa.md` | Tests, contract alignment, live metrics, the Impact numbers |
| Leader | `leader.md` | Integration, approval through the API, fallbacks, demo mode |

## Rules for everyone

1. Open a Pull Request as soon as one piece works, even a partial one. Do not wait until everything is finished.
2. Work only in your own folder. If you need a change elsewhere, ask the Leader.
3. Your agent's output must follow `docs/agent_contracts.md`. Do not change the contracts yourself.
4. Every real agent needs a `real` or `stub` fallback and at least one pytest test.
5. Fill your `bob_sessions/*.md` file: the task you gave Bob, what it produced, the Bob features used, and your screenshots.
6. Run `git pull origin main` before you start and before you open a PR.
7. Message the Leader when you are blocked. Do not wait.

## Decisions for the demo (read this)

1. **Two planted bugs in `backend/demo_bug.py`:** bug 1 = missing ownership check on DELETE (found by the tests, fixed by the debug agent); bug 2 = a hard-coded secret (found and fixed by the security agent). This keeps both stories separate. Manar adds bug 2 to the file (without changing the 20 tests); Haytam's agent finds and fixes it.
2. **Restore before every run:** `python tests/restore_demo_bug.py` puts the file back in its buggy state. Never commit the fixed version of `demo_bug.py`.
3. **Plan output:** one fixture only, `fixtures/plan_output.json`.

## Shared facts

- Stage names in the orchestrator: `plan`, `build`, `test`, `debug`, `security`, `fix`. Register an agent with `orchestrator.agents_base.register_agent("<stage>", YourAgent())`.
- Every agent returns an `AgentResult` (`orchestrator/contracts.py`).
- Plan result keys the gate reads: `data["requirements"]` (at least 5) and `data["architecture"]["adr"]` (at least 1).
- Test result keys: `total`, `passed`, `failed`, `failures`, `coverage_percent`. The gate passes only if `passed == total`.
- Security result keys: `verdict` (`PASS` or `BLOCKED`), `counts`, `findings` (each finding follows `SecurityFinding`). The gate blocks on `critical` or `high`.
- The demo bug: `backend/demo_bug.py`, function `delete_task` (no ownership check, CWE-639).
- Run the orchestrator: `python -m orchestrator.run --idea "task management SaaS" --auto-approve`.
