# Next tasks (round 3, final)

Updated 27 Sep 2026. Read `docs/STATUS.md` first: it says what is done and verified. Each person has a file here with what is left.

| Person | File | Main goal |
|---|---|---|
| Fati | `fati.md` | The dashboard page in `frontend/static/` |
| Haytam | `haytam.md` | Real fix agent and the hard-coded-secret rule, in one PR |
| Manar | `manar.md` | Insights endpoints if needed, test clean-up, demo speech |
| Safa | `safa.md` | Insights endpoints and screen, honest Impact numbers |
| Leader | `leader.md` | Review and merge, final checks, video, slides, submission |

## Rules for everyone

1. Branch from the latest `main` (`git fetch origin && git checkout -b <new-branch> origin/main`). Open a Pull Request as soon as one piece works, even a partial one.
2. Work only in your own files. If you need a change elsewhere, ask the Leader.
3. Follow `docs/agent_contracts.md` and `docs/API.md`. Do not change them yourself.
4. Every real agent needs a stub fallback and at least one pytest test. Run `python -m pytest -q` before you open a PR.
5. Never commit the fixed version of `backend/demo_bug.py`. `python tests/restore_demo_bug.py` puts the bug back.
6. Message the Leader when you are blocked. Do not wait.

## Done so far (verified on a fresh clone of `main`)

Orchestrator, gates, retries, parallel checks, approval broker, real testing / debug / security agents, plan agent (replays a saved Bob plan), memory and metrics wiring, backend API (create, start, status, approve, reset), offline terminal demo (`scripts/demo.py`), README with diagram, slides, 128 tests.

## Still open

1. Dashboard page (Fati).
2. Real fix agent and secret rule (Haytam).
3. Insights endpoints and screen, Impact numbers (Safa; Manar takes the endpoints if she cannot).
4. Backup video, rehearsals, final checks and submission (Leader and everyone).

## Shared facts

- Stage names: `plan`, `build`, `test`, `debug`, `security`, `fix`. Register with `orchestrator.agents_base.register_agent("<stage>", YourAgent())`.
- Every agent returns an `AgentResult` (`orchestrator/contracts.py`). Plan result keys: `data["requirements"]` (at least 5) and `data["architecture"]["adr"]` (at least 1). Test keys: `total`, `passed`, `failed`, `failures`, `coverage_percent` (passes only if `passed == total` and total is above 0). Security keys: `verdict`, `counts`, `findings` (blocks on `critical` or `high`).
- The demo app is `backend/demo_bug.py`: bug 1 = missing ownership check in `delete_task` (CWE-639, found by the tests and the scanner, fixed by the Debugger); bug 2 = hard-coded secret `API_SECRET_KEY` (currently rated LOW by the scanner, so it does not block).
- Run everything: `python scripts/demo.py` (terminal) or `uvicorn backend.main:app` (API, page at `/`).

## Timeline

| When | Everyone | Leader |
|---|---|---|
| Now | Push what works and open PRs | Review and merge each PR, rerun the fresh-clone test |
| Cut-off (set by the Leader) | Last merge. If the page is not merged, we demo the terminal version | Announce the freeze |
| After the freeze | Only fixes that break a rehearsal. Two timed rehearsals (`docs/DEMO_PLAN.md`) | Final fresh-clone test, backup video, submit |

## Demo roles

Leader: introduction, approval clicks, closing, and drives the screen. Fati: planning step. Manar: tests and debug. Haytam: security. Safa: memory and impact. Details and timing: `docs/DEMO_PLAN.md`.
