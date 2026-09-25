# DevForge: Architecture and Roles

Source: the shared ChatGPT chat "Hackathon guide summary". The project is DevForge, an AI Software Development Lifecycle Orchestrator for a 48-hour hackathon, built by 6 people with IBM Bob as a core tool.

---

## 1. What DevForge is

DevForge is **not** a plain AI code generator. It orchestrates the whole development lifecycle using specialized AI agents and explicit quality gates:

```
IDEA -> DISCOVERY -> RESEARCH -> REQUIREMENTS -> ARCHITECTURE -> MILESTONES
     -> BUILD -> TEST -> DEBUG -> CODE REVIEW -> SECURITY -> PERFORMANCE
     -> SEO -> FINAL REVIEW -> HUMAN APPROVAL -> RELEASE
```

**Minimum viable version (never sacrifice this):**
`IDEA -> PLAN -> BUILD -> TEST -> DEBUG -> SECURITY -> HUMAN APPROVAL -> RELEASE`

---

## 2. System architecture (layers)

```
                       USER IDEA
                           |
                           v
                  MAIN ORCHESTRATOR  (state machine, gates, routing)
                           |
      +--------------------+---------------------+
      v                    v                     v
 INTELLIGENCE AGENTS   BUILD/QUALITY AGENTS   MEMORY & METRICS
 Research              Builder                 Decision Memory
 Requirements          Testing                 Evaluation / Impact
 Architecture          Debugger
                       Code Review
                       Security Red-Team
                       Performance / SEO
      |                    |                     |
      +--------------------+---------------------+
                           v
              BACKEND API (FastAPI + PostgreSQL)
                           v
              DASHBOARD (Next.js): live project pipeline
```

**Suggested stack (do not expand it):** Next.js, TypeScript, Tailwind, FastAPI, PostgreSQL, Docker.

**Repository layout**
```
devforge/
├── frontend/       dashboard (Ali)
├── backend/        API, DB, project state (Ali)
├── orchestrator/   state machine, routing, gates (Leader)
├── agents/         research, requirements, architecture, testing, debug (Fati, Manar)
├── security/       red-team agent, security gate (Haytam)
├── memory/         decision memory + metrics (Safa)
├── tests/
├── docs/           ARCHITECTURE.md, agent_contracts.md
├── bob_sessions/   Bob evidence (session summaries/screenshots)
├── DATA_SOURCES.md
└── README.md
```

---

## 3. Components and their roles

### 3.1 Main Orchestrator (the brain)
- Decides which agent runs when, and what each receives and outputs.
- Owns the state machine and the pass/fail rules of every quality gate.
- Decides what can run in parallel, and when a human must approve.
- Handles retries, escalation and error handling.

### 3.2 Agents

| Agent | Role | Input -> Output |
|---|---|---|
| Research Agent | Market, technical and competitor research | Idea -> research report with sources, risks, technology options |
| Requirements Agent | Turns the idea into buildable specs | Idea/research -> user stories, functional and non-functional requirements, acceptance criteria, constraints |
| Architecture Agent | Designs the solution | Requirements -> frontend, backend, DB, APIs, auth, infrastructure, and an Architecture Decision Record |
| Planning/Milestone Agent | Splits work into milestones | Architecture -> ordered milestones |
| Builder Agent | Implements a milestone | Milestone -> code |
| Testing Agent | Proves the code works | Milestone/code -> generated tests, run results (e.g. 17/20 pass) |
| Debugger Agent | Fixes failures | Failing tests + logs -> root cause, fix, re-run |
| Code Review Agent | Reviews quality | Code -> review verdict |
| Security Red-Team Agent | Attacks the code (auth, authorization, input validation, API security, secrets, dependencies, SQLi, XSS, CSRF, config) | Code -> security report by severity, PASS/BLOCKED |
| Fix Agent | Patches findings | Finding -> patch -> retest |
| Performance / SEO Agents | Final quality checks | Build -> report |
| Release Agent | Prepares the release | Approved build -> release |
| Decision Memory Agent | Records and serves decisions | Decision events -> queryable memory |

Keep it to a small number of strong agents. The MVP does not need all of them.

### 3.3 Quality gates
Each gate has explicit PASS/FAIL criteria, and a FAIL either loops back (retry) or stops for a human. Gates exist for: requirements, architecture, milestone, tests, code review, security, performance, SEO, final release.

### 3.4 Milestone state machine
```
MILESTONE_CREATED -> BUILDING -> TESTING
TESTING --FAILED--> DEBUGGING -> TESTING
TESTING --PASSED--> REVIEW -> APPROVED -> NEXT_MILESTONE
```

### 3.4 Parallel execution
After BUILD, these can run in parallel and the orchestrator merges their results:
```
BUILD -+-> Testing Agent
       +-> Code Review Agent
       +-> Security Agent
       +-> Documentation Agent
```

### 3.5 Human-in-the-loop
Mandatory approval for: architecture, major DB/schema changes, major dependency changes, destructive operations, and final release. The human should see the gate results and evidence before approving.

### 3.6 Error handling
Defined behavior for: agent failure, test failure, security finding, agents disagreeing, a fix that causes a regression, and repeated failures. Use retry limits, then escalate to a human.

### 3.7 Project Memory
Each key decision is stored with question, alternatives, decision, reason, source and date. Future agents can query it.
Example: *Decision #07, database choice. PostgreSQL over MongoDB and MySQL, because the data is relational and needs transactions.*

### 3.8 Data contracts
Objects exchanged between agents: `ProjectContext`, `Requirement`, `Milestone`, `AgentResult`, `TestResult`, `SecurityFinding`, `Decision`, `GateResult` (documented in `docs/agent_contracts.md`).

### 3.9 Backend API (only what the demo needs)
```
POST /projects            POST /projects/{id}/start     GET /projects/{id}/status
POST /milestones          GET  /milestones
POST /agents/run          GET  /agents/status
GET  /tests               GET  /security                GET /decisions
```

### 3.10 Dashboard
Screens: Project Overview, Requirements, Architecture, Milestones, Agent Activity, Testing, Security, Decision Memory, Release. The key screen is the **Live Project Pipeline** (a checklist such as ✓ Requirements, ✓ Architecture, ⚙ Milestone 2 BUILDING, ○ Testing, ○ Security, ○ Release).

### 3.11 IBM Bob's role
Every member must use Bob meaningfully (Plan, Agent, subagents, parallel tasks, task management, code review) and save evidence in `bob_sessions/`. The leader uses Bob for architecture planning, orchestration structure, subagent design, integration and final code review. The chat says not to invent Bob capabilities: any uncertain one must be marked for verification.

---

## 4. Team roles

| Member | Role | Owns | Deliverables |
|---|---|---|---|
| **You (Leader + AI)** | Product/AI lead, orchestrator | Main orchestrator, state machine, agent communication, quality gates, integration, final architecture, demo | `docs/ARCHITECTURE.md`, `orchestrator/` |
| **Ali (AI + Web)** | Full-stack lead | Dashboard, backend API, DB, project state, orchestrator to backend to frontend link | `frontend/`, `backend/` |
| **Haytam (Cybersecurity)** | Security lead | Security Red-Team Agent, security gate, Fix/Retest loop; plants one intentional vulnerability for the demo | `security/` |
| **Fati (AI)** | Agent engineer | Research, Requirements and Architecture agents (every research claim needs a source) | `agents/research_agent`, `requirements_agent`, `architecture_agent`, `docs/agent_contracts.md` |
| **Manar (AI)** | QA / testing | Testing Agent, Debugger Agent, regression testing; plants one intentional bug for the demo | `agents/` testing and debug, `tests/` |
| **Safa (AI)** | Memory + evaluation | Decision Memory, metrics (times, tests, bugs, vulnerabilities, retries, human interventions), "DevForge Impact" dashboard using only real numbers | `memory/` |

---

## 5. Who works with whom

| Pair/group | Collaborate on |
|---|---|
| You + Fati | Agent inputs/outputs and how agents talk to the orchestrator |
| You + Ali | Orchestrator to backend API to frontend (integrate early, not at the end) |
| Manar + Haytam | Shared PASS/FAIL/FINDING/SEVERITY/FIX/RETEST format; testing then security, merged into one quality gate |
| Safa + Fati | Research and architecture decisions stored in memory |
| Safa + Ali | Memory, metrics and agent status shown on the dashboard |
| Ali + Manar / Haytam | Test and security results displayed in the dashboard |

**Parallelism:** all six can start immediately (leader on orchestrator, Fati on intelligence agents, Ali on dashboard/API, Manar on testing, Haytam on security, Safa on memory/metrics). Sync every 4-6 hours.

```
              YOU (architecture)
       +--------+---------+
       v        v         v
     FATI      ALI       SAFA
       +--------+---------+
                v
              MANAR (test/debug)
                v
              HAYTAM (security)
                v
          YOU + ALI (integration) -> DEMO
```

---

## 6. 48-hour timeline

| Phase | Hours | Focus |
|---|---|---|
| 1 | 0-4 | Setup (Bob accounts, repo, branches), everyone starts their stream |
| 2 | 4-12 | First end-to-end flow: idea -> requirements -> architecture -> milestone -> build -> test |
| 3 | 12-24 | Add debugging, security, decision memory, dashboard integration |
| 4 | 24-36 | Performance, SEO, quality gates, human approval, metrics; run the full workflow several times |
| 5 | 36-42 | Feature freeze: bugs, integration, UI, demo data, Bob evidence, README, diagrams |
| 6 | 42-48 | Demo rehearsal |

---

## 7. Demo flow (about 4 minutes)

1. Developer gives an idea (demo app: a simple task-management SaaS)
2. DevForge researches and plans
3. Requirements and architecture are generated
4. A milestone is built
5. A test intentionally fails (17/20)
6. Debugger finds the root cause and fixes it (20/20)
7. Security agent finds a vulnerability (gate fails)
8. Vulnerability is fixed and retested (gate passes)
9. All quality gates pass
10. Human approves the release

---

## 8. Recommended next steps from the chat
1. Give Bob the "Lead Software Architect" prompt (13-section architecture request) in Plan mode.
2. Then have Bob review and simplify its own architecture ("Technical Architect" prompt) into a final MVP architecture.
3. Produce one architecture diagram showing the 8-10 agents, their inputs/outputs, the milestone state machine, and where Bob is used.
