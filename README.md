# DevForge

**An AI Software Development Lifecycle Orchestrator**, built for the IBM Bob hackathon.

DevForge is not just an AI code generator. It orchestrates the whole development lifecycle with specialized AI agents and explicit quality gates, and it keeps a human in the loop for the decisions that matter.

```
Idea -> Plan (research, requirements, architecture) -> Build -> Test -> Debug -> Security -> Fix -> Human approval -> Release
```

## The problem

Developers lose a lot of time coordinating requirements, implementation, testing, debugging, security review and release preparation, and AI code generators skip most of these steps.

## The solution

A central orchestrator drives a project through a state machine. Specialized agents do each stage, and quality gates with clear PASS/FAIL rules decide whether the project may move on.

| Stage | Agent | Gate rule |
|---|---|---|
| Plan | Plan agent (research, requirements, architecture) | Plan gate; human approves the architecture |
| Build | Builder agent | none |
| Test | Testing agent | PASS only if 100% of tests pass |
| Debug | Debugger agent | loops back to Test (max 3 retries) |
| Security | Security red-team agent | BLOCKED if any critical or high finding |
| Fix | Fix agent | loops back to Test and Security (max 2 retries) |
| Release | Human approval | required before RELEASED |

When retries run out, the project stops in the `FAILED` state and asks for a human.

The demo shows the whole story: tests fail (17/20), the Debugger fixes them (20/20), the security agent finds a vulnerability, the Fix agent patches it, all gates pass, and a human approves the release.

## Architecture

- Full design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Data contracts shared by all agents: [`docs/agent_contracts.md`](docs/agent_contracts.md)
- Orchestrator details and how to plug in a real agent: [`orchestrator/README.md`](orchestrator/README.md)
- Task assignment per team member: [`docs/tasks/README.md`](docs/tasks/README.md)

**Stack:** Python (orchestrator, agents, FastAPI), Next.js + TypeScript + Tailwind (dashboard), PostgreSQL, Docker, IBM Bob.

## Repository layout

```
orchestrator/   state machine, runner, gates, human approval, stub agents   (Leader)
agents/         research, requirements, architecture, testing, debug agents (Fati, Manar)
security/       security red-team agent and gate                            (Haytam)
memory/         decision memory and metrics                                 (Safa)
backend/        FastAPI API                                                 (Ali)
frontend/       Next.js dashboard                                           (Ali)
config/         gate thresholds and retry limits
tests/          unit and end-to-end tests
docs/           architecture, contracts, tasks
bob_sessions/   evidence of how IBM Bob was used
```

## Run the orchestrator

```bash
pip install pydantic pytest
python -m orchestrator.run --idea "task management SaaS"                  # asks for human approval
python -m orchestrator.run --idea "task management SaaS" --auto-approve   # no prompts
python -m pytest -q                                                       # tests
```

The run writes `logs/orchestrator.jsonl` (events) and `data/project_state.json` (current state).

## How IBM Bob was used

Every team member used Bob for a real part of the build, with sessions recorded in [`bob_sessions/`](bob_sessions/). The leader used Bob (Plan and Agent modes) for the architecture, the data contracts and the orchestrator.

## Team

| Member | Role |
|---|---|
| Fatima Ezzahrae | Team leader, AI: orchestrator, contracts, integration |
| Ali | AI and web development: dashboard and backend |
| Haytam | Cybersecurity: security agent and gate |
| Fati | AI: research, requirements and architecture agents |
| Manar | AI: testing and debugging agents |
| Safa | AI: decision memory and metrics |

## Team workflow

One branch per person (`<name>/<area>`), work only in your own folder, open a Pull Request into `main`, and the leader reviews and merges. Never push directly to `main`.
