# Fati — Agent Engineer

## Role
Agent engineer. Turn "I have an idea" into "here is exactly what to build".

## Branch and Folders
- **Branch:** `fati/agents`
- **Folders:** `agents/research_agent/`, `agents/requirements_agent/`, `agents/architecture_agent/`

---

## Objective
Build the three intelligence agents that transform a raw idea into a fully specified, architecturally sound plan — ready to hand to the Builder Agent.

---

## Context
DevForge orchestrates: **Idea → Research → Requirements → Architecture → Milestones → Build → Test → Debug → Security → Human Approval → Release**.
Your three agents cover the first three stages. They run sequentially: Research output feeds Requirements; Requirements output feeds Architecture.
Demo app idea: *"Build a simple task-management SaaS for small teams."*
Stack: Next.js + TypeScript + Tailwind, FastAPI, PostgreSQL, Docker. Do not expand it.

Every agent returns:
```json
{ "agent": "...", "status": "PASS | FAIL | ERROR", "summary": "...", "data": {}, "duration_seconds": 0, "timestamp": "..." }
```

The Leader publishes the full contracts in `docs/agent_contracts.md` around **hour 3**. Until then, use the shape above.

---

## Deliverables

- [ ] **Research Agent** (`agents/research_agent/agent.py`)
  - Input: `{ "idea": "..." }`
  - Output `data` field:
    ```json
    {
      "market_overview": "...",
      "competitors": ["..."],
      "existing_solutions": ["..."],
      "technical_constraints": ["..."],
      "technology_recommendations": ["..."],
      "risks": ["..."],
      "sources": ["url or reference for every claim"]
    }
    ```
  - **Every factual claim must have a source. List all sources in `DATA_SOURCES.md`.**

- [ ] **Requirements Agent** (`agents/requirements_agent/agent.py`)
  - Input: Research Agent output
  - Output `data` field:
    ```json
    {
      "functional_requirements": ["..."],
      "non_functional_requirements": ["..."],
      "user_stories": [
        { "id": "US-001", "as_a": "...", "i_want": "...", "so_that": "...", "acceptance_criteria": ["..."] }
      ],
      "constraints": ["..."],
      "risks": ["..."]
    }
    ```

- [ ] **Architecture Agent** (`agents/architecture_agent/agent.py`)
  - Input: Requirements Agent output
  - Output `data` field:
    ```json
    {
      "frontend": "...", "backend": "...", "database": "...",
      "apis": ["..."], "authentication": "...", "infrastructure": "...",
      "dependencies": ["..."],
      "adr": [{ "id": "ADR-001", "decision": "...", "reason": "...", "alternatives": ["..."] }]
    }
    ```

- [ ] All three agents return the standard `AgentResult` JSON and can be run with `python -m agents.research_agent.agent`.
- [ ] **Bob evidence:** `bob_sessions/fati_task01_research_agent.png`, `fati_task02_requirements_agent.png`, `fati_task03_architecture_agent.png`.

---

## Dependencies

| Depends on | What you need |
|---|---|
| **Leader** | How agents are invoked by the orchestrator; the full `AgentResult` contract (hour 3) |
| **Safa** | Architecture ADR decisions must be stored in memory via `memory_agent.store()` — coordinate the Decision schema |

---

## Bob Task
Use **Bob Plan mode** to design each agent's logic, then **Bob Agent mode** to implement it.
1. Run the prompt below for the Research Agent first.
2. Screenshot → `bob_sessions/fati_task01_research_agent.png`.
3. Repeat for Requirements Agent → `fati_task02_requirements_agent.png`.
4. Repeat for Architecture Agent → `fati_task03_architecture_agent.png`.

---

## Definition of Done
- [ ] All three agents run on the demo idea and produce valid `AgentResult` JSON saved to a file.
- [ ] `DATA_SOURCES.md` lists at least one source per Research Agent claim.
- [ ] Architecture Agent output includes at least one ADR entry.
- [ ] All three Bob session screenshots saved in `bob_sessions/`.

---

## Deadline — First Sync (~hour 4)
Have all three agent stubs returning hard-coded valid JSON for the demo idea. The actual LLM-powered logic comes in Day 1 afternoon. Share your screen and confirm the `AgentResult` shape with the Leader.

---

## Bob Prompt

```
You are an expert Python AI engineer building intelligence agents for a software lifecycle orchestrator.

CONTEXT
Project: DevForge — an AI Software Development Lifecycle Orchestrator.
You are building three agents: Research Agent, Requirements Agent, Architecture Agent.
They run in sequence: Research → Requirements → Architecture.
Demo idea they will process: "Build a simple task-management SaaS for small teams."
Stack the architecture agent should recommend: Next.js + TypeScript + Tailwind, FastAPI, PostgreSQL, Docker.
Do not recommend any other stack.

AGENT RESULT SHAPE (all agents must return this):
{ "agent": "...", "status": "PASS | FAIL | ERROR", "summary": "...",
  "data": {}, "duration_seconds": 0, "timestamp": "..." }

TASK
1. Create agents/research_agent/agent.py
   Class: ResearchAgent
   Method: run(idea: str) -> dict
   Returns AgentResult where data contains:
   { market_overview, competitors (list), existing_solutions (list),
     technical_constraints (list), technology_recommendations (list),
     risks (list), sources (list — one URL or reference per claim) }

2. Create agents/requirements_agent/agent.py
   Class: RequirementsAgent
   Method: run(research_result: dict) -> dict
   Returns AgentResult where data contains:
   { functional_requirements (list), non_functional_requirements (list),
     user_stories (list of {id, as_a, i_want, so_that, acceptance_criteria}),
     constraints (list), risks (list) }

3. Create agents/architecture_agent/agent.py
   Class: ArchitectureAgent
   Method: run(requirements_result: dict) -> dict
   Returns AgentResult where data contains:
   { frontend, backend, database, apis (list), authentication,
     infrastructure, dependencies (list),
     adr (list of {id, decision, reason, alternatives}) }

4. For now, implement each agent as a STUB that returns realistic hard-coded demo data
   for the task-management SaaS idea. The real LLM calls will be added later.

5. Create agents/__init__.py and agents/research_agent/__init__.py,
   agents/requirements_agent/__init__.py, agents/architecture_agent/__init__.py.

6. Each agent must be runnable as:
   python -m agents.research_agent.agent

CONSTRAINTS
- Pure Python 3.11, no external API calls yet (stubs only).
- Use datetime.utcnow().isoformat() + "Z" for timestamps.
- Use time.time() to compute duration_seconds.
- Keep each file under 100 lines.

OUTPUT FORMAT
File tree first, then each file in full.
```
