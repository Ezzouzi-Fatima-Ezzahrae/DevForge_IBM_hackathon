# Fati: next tasks

**Branch:** `fati/agents`. **Folders:** `agents/plan_agent.py`, `agents/prompts/`, `fixtures/`, `DATA_SOURCES.md`.

## Status (reviewed)
Merged into `main`. Done and good: the Bob Plan session, a saved plan (6 user stories with acceptance criteria, stack, 9 endpoints, 3 ADRs), the prompt, a Plan Gate test that passes, and a full Bob session summary. The saved plan follows the contracts and the decisions match the `Decision` format.

## Problems to fix

- The orchestrator does not use your agent yet: `agents_base.py` still registers the stub.
- `agents/plan_agent.py` is a plain function (`run(input)`), not an agent class.
- The decisions contain a fixed `project_id` (`proj_task_management`), so they will not match the id of the running project.
- `DATA_SOURCES.md` is empty.
- Two fixture files: `fixtures/plan_output.json` (real) and `tests/fixtures/plan_output.json` (empty).

## Tasks (in order)

1. **Make it an agent.** In `agents/plan_agent.py` add `class PlanAgent(BaseAgent)` with `run(self, context: ProjectContext) -> AgentResult`, which loads the saved plan and **sets `project_id` in every decision from `context.project_id`** and the idea from `context.idea`. Keep the function `run(input)` if your test uses it.
2. **Never crash:** if the fixture is missing or invalid, return `AgentResult(status=ERROR)` with a clear summary.
3. **Tell the Leader** when it is ready; the Leader registers it as the `plan` stage (or you may register it in your own code with `register_agent("plan", PlanAgent())`, keeping the stub as a fallback).
4. **Sources:** add real sources to `DATA_SOURCES.md` for the claims in your plan (for example, why PostgreSQL for relational data, JWT for stateless auth). Only include sources you actually consulted.
5. **Tests** in `tests/test_agents.py`: the valid plan passes the gate (you have this), a plan with fewer than 5 stories fails, a plan without an ADR fails, and the decisions carry the context's `project_id`.
6. **One fixture:** keep `fixtures/plan_output.json` and delete or fill `tests/fixtures/plan_output.json`.
7. **Second plan variant (optional):** if time allows, save a second, different idea so the demo can show that the agent is not hard-coded to one idea.
8. **Demo:** prepare to explain the planning step in 30 seconds (Bob Plan mode, what came out, the ADRs).

## Done when
`python -m orchestrator.run --idea "task management SaaS" --auto-approve` shows your PlanAgent (not the stub) and the decisions appear in `memory/data/decisions.json` with the correct project id.

## Talk to
Leader (registration), Safa (decision storage).
