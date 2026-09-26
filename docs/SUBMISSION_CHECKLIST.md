# Submission checklist

Check each item on a **fresh clone** of `main` (`git clone <repo> test-clone`). Verify the required format and deadline in the hackathon guide, because they were not checked here.

## Repository
- [ ] `README.md` explains the problem, the solution, the architecture and how to run it, in a way a stranger can follow
- [ ] `docs/ARCHITECTURE.md`, `docs/agent_contracts.md`, `docs/STATUS.md` are current
- [ ] Architecture and state-machine diagram in `docs/`
- [ ] `requirements.txt` (Python) and the dashboard's `package.json` exist, and installing from them works
- [ ] `.env.example` has names only; no secrets, keys or `.env` in the repository (search: `git grep -i -E "secret|password|token|api_key"`)
- [ ] `backend/demo_bug.py` is the **buggy** version (`python tests/restore_demo_bug.py`)
- [ ] `logs/` and generated data files are not committed
- [ ] `DATA_SOURCES.md` lists the real sources

## It works
- [ ] `python -m pytest -q` passes
- [ ] `python -m orchestrator.run --idea "task management SaaS" --auto-approve` ends in RELEASED
- [ ] The backend starts, the dashboard shows the pipeline live, Approve leads to RELEASED
- [ ] Two runs in a row give the same result (restore between runs)
- [ ] Each real agent has a working stub fallback
- [ ] The retry limits work: the pipeline ends in FAILED, not in a loop

## Bob evidence
- [ ] Every member has a filled `bob_sessions/<name>_*.md` (task, what Bob produced, Bob features used, screenshots)
- [ ] Screenshots are readable and contain no secrets
- [ ] The Bob features used are named: Plan mode, Agent mode, task list, and others if used

## Demo
- [ ] Full 4-minute run timed at least 4 times (`docs/DEMO_PLAN.md`)
- [ ] Video of a successful run recorded as a backup
- [ ] Slides finished; each speaker knows their part
- [ ] The "DevForge Impact" numbers come from real runs only

## Team
- [ ] Every member's work is merged into `main` (no important work left only on a branch)
- [ ] Final `git pull` done by everyone, and the demo machine runs the final `main`
