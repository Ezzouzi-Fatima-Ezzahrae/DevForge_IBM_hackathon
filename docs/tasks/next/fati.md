# Fati: next tasks

**Branch:** `fati/agents`. **Folders:** `agents/plan_agent.py`, `agents/prompts/`, `fixtures/`, `DATA_SOURCES.md`.

## Status (reviewed)
Done and connected: `PlanAgent` extends `BaseAgent`, takes `project_id` and `idea` from the context, returns an ERROR when the fixture is missing or invalid, has gate tests (fewer than 5 stories, no ADR, project id), and `DATA_SOURCES.md` has 3 sources. The Leader registered it as the `plan` stage (with a fallback to the stub), and the full pipeline runs with it. Two small edits were made to your file: it now reports the real duration and the current time (the fixture said 4.21 seconds, which would have polluted the impact numbers), and it marks its output as a replay of the saved Bob session.

## What is left

1. **Bob evidence:** add your screenshots to `bob_sessions/` and name the Bob features used in `fati_plan_agent_session.md`.
2. **A second saved plan** for a different idea (optional but valuable): save it as `fixtures/plan_output_<name>.json` and let `PlanAgent` pick the fixture by keyword, so the demo does not look hard-coded. Right now every idea returns the task-management plan.
3. **Research and requirements evidence:** in `DATA_SOURCES.md`, add the source for each technical claim you make in the demo (PostgreSQL, JWT, Next.js are done).
4. **Help the team:** you have the most free time now. Ask Ali if he wants help with the dashboard, or Manar with test cases.

## Demo role
Fati speaks about the planning step (about 30 seconds). Practice with the timer. See `docs/DEMO_PLAN.md`. Feature freeze is at hour 40; after that only fix bugs that break a rehearsal.
