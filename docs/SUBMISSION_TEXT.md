# Text for the lablab submission form

Copy each block into the matching field. Numbers are measured (see `docs/IMPACT.md`).

## Project title
DevForge: an AI orchestrator for the whole software lifecycle

## Short description
DevForge drives a project from idea to release with specialised AI agents and quality gates: plan, build, test, debug, security scan and a human approval, with failures looping back to the right agent.

## Long description
AI code generators write code, but nobody proves it works, nobody checks it is safe, and nobody decides who may release it. DevForge is not a code generator. It is an orchestrator for the whole development lifecycle.

A state machine takes an idea through Plan, Build, Test, Debug, Security, Fix and Release. Specialised agents do each stage, and explicit quality gates decide whether the project may move on: the tests gate passes only at 100%, the security gate blocks on any critical or high finding, and only a human can release. Tests and the security scan run in parallel. When a gate fails, the project loops back to the right agent (Debugger or Fix) with retry limits; when retries run out, it stops and asks a human.

In the demo, a small task-management API contains a planted access-control bug (CWE-639: any user can delete another user's task). The test agent runs the real test suite and reports 17/20. In parallel, the security agent finds the same flaw as a HIGH finding and blocks the release. The Debugger finds the root cause, patches the real file and reruns the tests: 20/20. Both gates pass, a human approves the release, and the project is RELEASED. Across 3 measured runs the result was identical: 17/20 to 20/20, 1 blocking finding, 2 retries, 2 human approvals.

DevForge also records every decision and metric in a queryable memory, exposes the pipeline through a FastAPI backend (start, live status, approve, reset, insights) and ships a narrated terminal demo that works offline.

Transparency: the test, debug and security agents and the orchestrator are real. The plan agent replays a saved IBM Bob Plan session, and the build and fix agents are stubs.

## IBM Bob usage statement
IBM Bob IDE was used by every team member and is documented in `bob_sessions/` (21 task screenshots plus a session file per member).
- Plan mode: the architecture and the state machine (Leader), and the requirements, user stories and decisions of the plan agent (Fati).
- Agent mode: the data contracts and the first version of the orchestrator (Leader; a long task tracked with Bob's task list until the Bobcoin budget was reached), the testing and debug agents (Manar), the decision memory and metrics (Safa), the security agent (Haytam).
- Code review with Bob: Safa's review of the memory APIs.
After Bob's budget was reached, the remaining fixes, the integration of all agents, the API, the tests and the demo were finished by the team with another AI assistant. The plan agent replays a saved Bob Plan session; it does not call Bob live. We do not present any simulated run as Bob's work.

## Business value
Teams lose time coordinating requirements, testing, debugging, security review and release, and AI-generated code adds review work because nothing proves it is correct or safe. DevForge automates the repeated loop (test, diagnose, patch, re-test, re-scan) with clear pass/fail rules and keeps a human decision at the release. It reduces manual effort and rework, catches the same defect two independent ways, and leaves an audit trail (event log, decision memory, gate results) for every run.

## Originality
- An orchestrator with quality gates and failure loops, not a code generator.
- Parallel test and security checks merged into one decision.
- A human-in-the-loop release with a timeout that never approves by accident.
- Honest by design: every agent is labelled REAL, REPLAY or STUB in the demo and the dashboard.

## Technology and category tags
IBM Bob, AI agents, developer productivity, DevOps, orchestration, testing, application security, human-in-the-loop, Python, FastAPI

## Public code repository
https://github.com/Ezzouzi-Fatima-Ezzahrae/DevForge_IBM_hackathon

## How to run
```
pip install -r requirements.txt
python scripts/demo.py                # narrated terminal demo
uvicorn backend.main:app --port 8000  # API and dashboard
python -m pytest -q                   # tests
```

## Demo application platform and URL
To fill in after hosting (for example Render or Hugging Face Spaces): start command `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.

## Video (5 minutes)
Full script, timings and recording steps: `docs/VIDEO_SCRIPT.md` (problem 0:00, live demo 0:30, business case 2:30, team and roadmap 4:00).
