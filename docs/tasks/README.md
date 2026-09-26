# DevForge — Team Task Overview

DevForge is an AI Software Development Lifecycle Orchestrator. It drives a project from idea to release using specialized AI agents and quality gates:

> **Idea → Research → Requirements → Architecture → Milestones → Build → Test → Debug → Security → Human Approval → Release**

Demo app: a simple task-management SaaS. Stack: Next.js + TypeScript + Tailwind, FastAPI, PostgreSQL, Docker. **Do not expand the stack.**

---

## Member Assignments

| Member | Branch | Folder(s) they own | First task (one line) | Deliverable at first sync (~hour 4) |
|---|---|---|---|---|
| **Leader** | `leader/orchestrator` | `orchestrator/` | Finalise `docs/ARCHITECTURE.md` and scaffold the orchestrator state machine | `orchestrator/state_machine.py` + `runner.py` with all transitions, stub agents and gates (done, see `orchestrator/README.md`) |
| **Ali** | `ali/platform` | `frontend/`, `backend/` | Scaffold Next.js dashboard + FastAPI backend with Docker Compose | App runs locally; pipeline page returns data from `GET /projects/{id}/status` |
| **Haytam** | `haytam/security` | `security/` | Stub the Security Agent and define the FindingResult JSON contract | `security/security_agent.py` stub + `tests/fixtures/security_finding_HIGH.json` |
| **Fati** | `fati/agents` | `agents/research_agent`, `agents/requirements_agent`, `agents/architecture_agent` | Write `docs/agent_contracts.md` and stub all three agents | All three agents return a valid `AgentResult` JSON when called |
| **Manar** | `manar/testing` | `agents/testing_agent`, `agents/debug_agent`, `tests/` | Stub Testing Agent + create demo fixtures (17/20 fail → 20/20 pass) | Tester stub + `tests/fixtures/test_fail_17_20.json` and `test_pass_20_20.json` |
| **Safa** | `safa/memory` | `memory/` | Implement `memory_agent.py` with `store()` and `query()` backed by PostgreSQL | A decision and a metric can be saved and read back through code |

---

## Who Works With Whom

| Pair / Group | Collaborate on |
|---|---|
| **Leader + Fati** | Agent input/output shapes; how each agent calls the orchestrator back |
| **Leader + Ali** | Orchestrator → backend API → frontend pipeline view wiring (integrate early) |
| **Manar + Haytam** | Shared `PASS/FAIL/FINDING/SEVERITY/FIX/RETEST` format; testing runs first, security runs after |
| **Safa + Fati** | Research and architecture decisions are stored in memory via `memory_agent.store()` |
| **Safa + Ali** | Memory query endpoint and DevForge Impact metrics panel shown on the dashboard |

---

## Team Rules

1. **Never push to `main` directly.** All work goes on your own branch.
2. **Work only inside your own folder(s).** Do not touch other members' folders without asking.
3. **Commit small and often.** Aim for one logical change per commit.
4. **Run `git pull origin main` every 2 hours** to stay in sync.
5. **Ask the Leader before changing shared files** — `docs/`, `docs/agent_contracts.md`, anything in `orchestrator/`.
6. **Never commit secrets or `.env` files.** Use `.env.example` for templates.
7. **Save Bob evidence in `bob_sessions/`** — at least one screenshot or session summary per task (e.g. `ali_task01_frontend.png`).

---

## How to Start

```bash
# 1. Switch to your branch
git checkout <your-branch>          # e.g. git checkout ali/platform

# 2. Sync with main
git pull origin main

# 3. Open your task file
# docs/tasks/ali.md  (or haytam.md / fati.md / manar.md / safa.md)
```

Read your task file top to bottom before writing any code. The first thing every member must do is run the Bob prompt at the bottom of their file and save the output screenshot to `bob_sessions/`.

---

## AgentResult Contract (all agents must return this shape)

```json
{
  "agent": "name_of_agent",
  "status": "PASS | FAIL | ERROR",
  "summary": "one-line human-readable result",
  "data": {},
  "duration_seconds": 0,
  "timestamp": "2025-07-15T10:00:00Z"
}
```

Full contracts will be published in `docs/agent_contracts.md` by the Leader around **hour 3**.
