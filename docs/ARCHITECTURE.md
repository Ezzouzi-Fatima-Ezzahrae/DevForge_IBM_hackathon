# DevForge — Final MVP Architecture

> **Technical Architect Review** — This document supersedes all prior drafts.
> It is the single source of truth for the 48-hour build.
> Every decision is driven by one question: *can six people ship this in 48 hours and demo it cleanly?*

---

## Table of Contents

1. [Critical Review — what was cut and why](#1-critical-review)
2. [Core Pipeline](#2-core-pipeline)
3. [Agent Table (6 agents)](#3-agent-table)
4. [Orchestrator State Machine](#4-orchestrator-state-machine)
5. [Quality Gates](#5-quality-gates)
6. [Parallelism and Merge](#6-parallelism-and-merge)
7. [Human Approval Points](#7-human-approval-points)
8. [Error Handling](#8-error-handling)
9. [Data Contracts (5 objects)](#9-data-contracts)
10. [IBM Bob Mapping](#10-ibm-bob-mapping)
11. [Folder Structure](#11-folder-structure)
12. [Backend API (10 endpoints)](#12-backend-api)
13. [Dashboard (3 screens)](#13-dashboard)
14. [48-Hour Timeline](#14-48-hour-timeline)
15. [Full Task Plan — Day 1 per member (H 0–24)](#15-day-1-task-plan)
16. [Full Task Plan — Day 2 per member (H 24–48)](#16-day-2-task-plan)
17. [Simplifications Summary](#17-simplifications-summary)
18. [4-Minute Demo Script](#18-demo-script)

---

## 1. Critical Review

### Over-engineered components — cut

| Was | Problem | Decision |
|---|---|---|
| Research Agent + Requirements Agent (separate) | Same input, same LLM, no real boundary between them | **Merged → Plan Agent** |
| Fix Agent | Identical to Builder given a finding as input | **Dropped — Builder handles fixes** |
| Milestone Planner (separate Bob session) | One LLM call that belongs inside the orchestrator | **Inlined into orchestrator** |
| Release Agent | "Release" is a status flag + changelog string | **Dropped — orchestrator sets RELEASED** |
| Code Review / Performance / SEO Agents | Not in the demo narrative | **Stubs returning PASS** |
| Vector search on Decision Memory | ~10 decisions fit in SQL `WHERE project_id = ?` | **Plain PostgreSQL** |
| Real-time WebSocket | Two days of infra, invisible to the audience | **3-second polling** |
| 9 dashboard screens | 8 are not in the demo | **3 screens only** |

### Bottlenecks fixed

- **Ali owns too much.** API surface trimmed to 10 endpoints scoped to what the demo actually calls.
- **Agent contracts blocked everyone.** All five contracts are defined in this document. Nobody waits.
- **LLM non-determinism during demo.** Agents run for real during development; the demo replays pre-recorded JSON fixtures. Zero live LLM calls during the 4-minute presentation.

### Likely integration failures — avoided

- Agents calling each other directly → eliminated. The orchestrator is the only router. Each agent exposes one function: `run(input: dict) → AgentResult`.
- Memory writes blocking the orchestrator → eliminated. All memory writes are async, fire-and-forget.
- Dashboard expecting streaming → eliminated. Dashboard polls `GET /projects/{id}/status` every 3 seconds; DB is always consistent.

---

## 2. Core Pipeline

```
IDEA
 │
 ▼
[1] PLAN AGENT        Research + Requirements + Architecture in one pass
 │                    Bob: Plan mode
 │  Gate: ≥5 user stories, consistent tech stack, ≥1 ADR
 │  FAIL → re-prompt (max 2×) → human
 ▼
[H] HUMAN APPROVES ARCHITECTURE
 │
 ▼
[2] MILESTONE PLANNER  (inlined in orchestrator — not a separate agent)
 │
 ▼
[3] BUILDER AGENT      Generates code for one milestone
 │                     Bob: Agent mode
 │
 ├─────────────────────────────────────┐
 ▼                                     ▼
[4a] TESTER AGENT             [4b] SECURITY AGENT     ← parallel
  Bob: Agent mode               Bob: Agent mode
  pytest / Jest                 Bandit / Semgrep
 │                                     │
 ▼                                     ▼
 Test gate                       Security gate
 PASS: ≥80%, 0 critical-path     PASS: 0 CRITICAL, 0 HIGH
 FAIL → [5] DEBUGGER (max 3)     BLOCKED → [3] fix (max 2)
 │                                     │
 └──────────── MERGE ──────────────────┘
                    │ both PASS
                    ▼
            MILESTONE APPROVED
                    │  (repeat per milestone)
                    ▼
[H] HUMAN APPROVES RELEASE
                    │
                    ▼
                 RELEASED
```

---

## 3. Agent Table

> Rule: if an agent does not appear in the pipeline above, it does not exist in the MVP.

| # | Agent | Owner | Input | Output | Bob usage |
|---|---|---|---|---|---|
| 1 | **Plan Agent** | Fati | `{idea, constraints}` | `requirements[], architecture, decisions[]` | Bob **Plan mode** |
| 2 | **Builder Agent** | Ali | `{milestone, architecture, prior_code}` | `files[], diff` | Bob **Agent mode** (file tools) |
| 3 | **Tester Agent** | Manar | `{milestone, files[]}` | `test_results[], pass_count, fail_count, coverage` | Bob **Agent mode** |
| 4 | **Debugger Agent** | Manar | `{failing_tests[], files[], logs}` | `patch_diff, root_cause, fixed: bool` | Bob **Agent mode** multi-step task |
| 5 | **Security Agent** | Haytam | `{files[], dependencies}` | `findings[], verdict: PASS\|BLOCKED` | Bob **Agent mode** + Bandit/Semgrep |
| 6 | **Memory Agent** | Safa | Any `Decision` or `GateResult` event | Stored record; context snippets on query | Bob **context injection** |

**Not built:** Code Review Agent, Fix Agent, Performance Agent, SEO Agent, Release Agent.  
**Stubs** (return `{"verdict": "PASS"}` immediately): Code Review gate.

---

## 4. Orchestrator State Machine

The orchestrator is a single Python class (`Orchestrator`) with an explicit state enum.
It is the **only** component that writes `project.status`.

```
States
──────
IDLE → PLANNING → BUILDING → TESTING → SECURED → AWAITING_APPROVAL → RELEASED
                                  ↕
                             DEBUGGING  (loop, max 3)
                                  ↕
               BUILDING ← SECURITY_FIX  (loop, max 2)

Transitions
───────────
IDLE              + create(idea)                → PLANNING
PLANNING          + plan_gate PASS              → BUILDING  (milestone 1)
PLANNING          + plan_gate FAIL, retry < 2   → PLANNING  (re-prompt with feedback)
PLANNING          + plan_gate FAIL, retry = 2   → HUMAN_REVIEW

BUILDING          + build done                  → TESTING   (fan-out: tester + security)

TESTING           + test_gate PASS              → check security result
TESTING           + test_gate FAIL, retry < 3   → DEBUGGING
TESTING           + test_gate FAIL, retry = 3   → HUMAN_REVIEW

DEBUGGING         + patch applied               → TESTING   (re-run tests)

check security    + sec_gate PASS               → MILESTONE_APPROVED
check security    + sec_gate BLOCKED, retry < 2 → SECURITY_FIX
check security    + sec_gate BLOCKED, retry = 2 → HUMAN_REVIEW

SECURITY_FIX      + patch applied               → TESTING   (re-run both)

MILESTONE_APPROVED + more milestones            → BUILDING  (next milestone)
MILESTONE_APPROVED + all done                   → AWAITING_APPROVAL

AWAITING_APPROVAL + human approves              → RELEASED
AWAITING_APPROVAL + human rejects               → BUILDING  (re-enter last milestone)
```

### Debug–Test retry loop

```
TESTING
  │ test_gate FAIL
  ▼
DEBUGGING  (Debugger Agent: root cause + patch)
  │
  ▼
TESTING  (re-run with patched code)
  │ PASS ──────────────────────► continue
  │ FAIL, retry < 3 ───────────► DEBUGGING again
  │ FAIL, retry = 3 ───────────► HUMAN_REVIEW (escalate with full log)
```

### Security-fix loop

```
SECURITY
  │ CRITICAL or HIGH findings
  ▼
SECURITY_FIX  (Builder patches specific file + line)
  │
  ▼
TESTING + SECURITY  (re-run both — patch can introduce regressions)
  │ PASS ──────────────────────► MILESTONE_APPROVED
  │ FAIL, retry < 2 ───────────► SECURITY_FIX again
  │ FAIL, retry = 2 ───────────► HUMAN_REVIEW
```

---

## 5. Quality Gates

### Gate 1 — Plan Gate

- **PASS:** ≥ 5 user stories each with one acceptance criterion; tech stack named; at least one ADR written.
- **FAIL action:** Re-invoke Plan Agent with failure reason appended to the prompt. Max 2 retries, then human review.

### Gate 2 — Test Gate (per milestone)

- **PASS:** ≥ 80 % of tests pass **and** zero critical-path failures (demo app: create task, list tasks, delete task with ownership check).
- **FAIL action:** Debugger Agent loop, max 3 iterations. Iteration 3 failure → human review with full failure log.

### Gate 3 — Security Gate (per milestone)

- **PASS:** Zero CRITICAL findings, zero HIGH findings. MEDIUM findings are logged but do not block.
- **BLOCKED action:** Builder Agent patches the affected file → rescan. Max 2 iterations, then human security review.

### Gate 4 — Release Gate

- **PASS:** All milestones APPROVED + all security gates PASS + human has clicked Approve.
- **FAIL:** Any open HIGH/CRITICAL finding or unapproved milestone. Human must resolve.
- **Human approval is always mandatory** — even on a clean PASS.

---

## 6. Parallelism and Merge

```
BUILD complete → immutable code snapshot
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
     Tester Agent             Security Agent     ← both in parallel
           │                         │
           └────────────┬────────────┘
                        ▼
                Orchestrator.merge()
                {test: GateResult, security: GateResult}
```

**Merge rules:**

- Overall = PASS only when both gate results are PASS.
- Both fail → fix security first (higher risk, smaller patch surface), then re-run both.
- Only testing fails → Debugger loop, then re-run both after the patch.

**Cannot run in parallel:**

- Plan → Build (strict sequential dependency on output).
- Debugger → Tester (patch must be applied before re-run).
- Any two agents writing to the same files.

---

## 7. Human Approval Points

Exactly two approval points. Fewer = cleaner demo.

| # | Point | Human sees | Actions |
|---|---|---|---|
| 1 | **Architecture sign-off** | User stories + ACs, tech stack, DB schema summary, ADR, gate result | Approve → continue · Request changes → re-plan |
| 2 | **Release sign-off** | All milestone statuses, test coverage %, security posture, decision log, changelog | Approve → RELEASED · Reject → back to last milestone |

The dashboard shows a **"Waiting for Human"** banner with the approval card inline.
No release action fires until `human_approved = true` is written to `ProjectContext`.

---

## 8. Error Handling

| Error | Max retries | Retry action | Escalation |
|---|---|---|---|
| Agent crash / timeout | 2 | Re-invoke same input | Status → ERROR; dashboard alert; human acts |
| Test gate FAIL | 3 debug cycles | Debugger → retest | Human review with full log |
| Security gate BLOCKED | 2 fix cycles | Builder patches → rescan | Human security review |
| Fix causes regression | 1 combined cycle | Debugger + Security re-run together | Immediate human review |
| Plan gate FAIL | 2 | Re-prompt Plan Agent with failure reason | Human clarifies idea |

Every retry increments `project.retries[stage]`. This counter is visible on the dashboard and written to memory.

---

## 9. Data Contracts

These five objects are the complete API surface between all components.
No agent passes anything outside these schemas. Full Pydantic schemas in `docs/agent_contracts.md`.

### ProjectContext

```json
{
  "project_id": "proj_abc123",
  "idea": "A task-management SaaS for small teams",
  "status": "TESTING",
  "current_milestone_index": 1,
  "milestones": [],
  "retries": { "plan": 0, "test": 1, "security": 0 },
  "human_approved_arch": false,
  "human_approved_release": false,
  "created_at": "2025-07-15T08:00:00Z"
}
```

### AgentResult

```json
{
  "agent": "tester_agent",
  "milestone_id": "ms_001",
  "status": "FAIL",
  "summary": "17/20 tests passed. 3 failures in DELETE /tasks/{id}",
  "payload": {},
  "duration_seconds": 38,
  "timestamp": "2025-07-15T10:30:00Z"
}
```

### TestResult

```json
{
  "id": "test_045",
  "name": "test_delete_task_not_owner",
  "status": "FAIL",
  "error": "AssertionError: expected 403, got 200",
  "file": "backend/routers/tasks.py",
  "line": 54,
  "is_critical_path": true
}
```

### SecurityFinding

```json
{
  "id": "SEC-012",
  "severity": "HIGH",
  "category": "broken_access_control",
  "description": "DELETE /tasks/{id} does not verify task ownership",
  "file": "backend/routers/tasks.py",
  "line": 54,
  "cwe": "CWE-639",
  "status": "OPEN"
}
```

### Decision

```json
{
  "id": "DEC-007",
  "question": "Which database?",
  "alternatives": ["PostgreSQL", "MongoDB"],
  "decision": "PostgreSQL",
  "reason": "Relational data, ACID transactions required",
  "source": "plan_agent",
  "timestamp": "2025-07-15T09:14:00Z"
}
```

---

## 10. IBM Bob Mapping

| DevForge function | Bob mode | Evidence file |
|---|---|---|
| Plan Agent: requirements + ADR | **Plan mode** | `bob_sessions/fati_plan_agent_session.md` |
| Builder Agent: writes code files | **Agent mode** (file tools) | `bob_sessions/ali_builder_session_ms001.md` |
| Tester + Security run concurrently | **Parallel subagents** *(verify concurrency limit)* | `manar_tester_session.md`, `haytam_security_session.md` |
| Memory injects prior decisions into prompts | **Context injection** | `bob_sessions/safa_memory_session.md` |
| Orchestrator tracks state transitions | **Agent mode** task management (todo list) | `bob_sessions/leader_orchestrator_session.md` |

**Rule:** every member saves ≥ 1 Bob session file before the demo.
Minimum content: prompt sent, output received, one-line note on what Bob decided.

---

## 11. Folder Structure

```
devforge/
├── frontend/                        # Next.js + TypeScript + Tailwind  (Ali)
│   ├── app/
│   │   ├── pipeline/page.tsx        # THE demo screen
│   │   ├── approval/page.tsx        # Human approval card
│   │   └── decisions/page.tsx       # Decision log + metrics
│   └── components/
│       ├── PipelineView.tsx
│       ├── GateBadge.tsx
│       └── ApprovalCard.tsx
│
├── backend/                         # FastAPI + PostgreSQL  (Ali)
│   ├── main.py
│   ├── routers/
│   │   ├── projects.py
│   │   ├── milestones.py
│   │   ├── agents.py
│   │   └── decisions.py
│   ├── models/
│   └── db.py
│
├── orchestrator/                    # (Leader)
│   ├── orchestrator.py              # FSM: states, transitions, gate evaluation
│   ├── gates.py                     # Pass/fail logic for each gate
│   └── runner.py                    # Parallel dispatch + result merge
│
├── agents/
│   ├── plan_agent.py                # (Fati)
│   ├── builder_agent.py             # (Ali)
│   ├── tester_agent.py              # (Manar)
│   ├── debugger_agent.py            # (Manar)
│   └── prompts/
│       ├── plan.md
│       ├── builder.md
│       ├── tester.md
│       └── debugger.md
│
├── security/                        # (Haytam)
│   ├── security_agent.py
│   ├── scanner.py                   # Bandit / Semgrep wrapper
│   └── gate.py
│
├── memory/                          # (Safa)
│   ├── memory_agent.py
│   ├── metrics.py
│   └── schemas.py                   # Pydantic: Decision, GateResult
│
├── tests/
│   ├── test_orchestrator.py
│   ├── test_gates.py
│   └── fixtures/
│       ├── plan_output.json
│       ├── build_output_ms001.json
│       ├── test_fail_17_20.json
│       ├── test_pass_20_20.json
│       ├── security_finding_HIGH.json
│       └── security_pass.json
│
├── docs/
│   ├── ARCHITECTURE.md              # ← this file
│   └── agent_contracts.md
│
├── bob_sessions/
│   ├── leader_orchestrator_session.md
│   ├── fati_plan_agent_session.md
│   ├── ali_builder_session.md
│   ├── manar_tester_session.md
│   ├── manar_debugger_session.md
│   ├── haytam_security_session.md
│   └── safa_memory_session.md
│
├── docker-compose.yml
├── .env.example
├── README.md
└── DATA_SOURCES.md
```

---

## 12. Backend API

Only what the dashboard and orchestrator actually call. Ali implements all 10 in the first 8 hours, even as mocks.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/projects` | Create project, return project_id |
| `POST` | `/projects/{id}/start` | Start the pipeline |
| `GET` | `/projects/{id}/status` | Poll current state (dashboard calls every 3 s) |
| `POST` | `/projects/{id}/approve` | Human approval action (arch or release) |
| `GET` | `/milestones?project_id=` | List milestones with statuses |
| `GET` | `/agents/results?project_id=` | All AgentResult records for a project |
| `GET` | `/tests?milestone_id=` | TestResult records |
| `GET` | `/security?milestone_id=` | SecurityFinding records |
| `GET` | `/decisions?project_id=` | Decision log |
| `GET` | `/metrics?project_id=` | KPI counters (bugs fixed, retries, time, vulns) |

---

## 13. Dashboard

Exactly three screens. Nothing more.

### Screen 1 — Pipeline View `/pipeline` ← the demo screen

Horizontal strip of stage cards. Each card: agent name, status badge, duration, short summary.
Clicking a card expands its detail (test failures or security findings).

```
[✅ PLAN] → [✅ BUILD] → [🔴 TEST 17/20] → [⚙ DEBUG] → [✅ TEST 20/20]
          → [🔴 SECURITY HIGH] → [⚙ FIX] → [✅ SECURITY] → [⏳ APPROVAL] → [✅ RELEASED]
```

### Screen 2 — Approval Card `/approval`

Shown when `project.status = AWAITING_APPROVAL`.
Contains the gate summary and two buttons: **Approve** / **Request Changes**.
Calls `POST /projects/{id}/approve`.

### Screen 3 — Decision Log `/decisions`

Table of all `Decision` records + the DevForge Impact metrics panel (real numbers only):
time elapsed, tests run/passed, bugs fixed, vulnerabilities found/fixed, retries, human interventions.

---

## 14. 48-Hour Timeline

| Hours | Focus | Hard output required |
|---|---|---|
| 0–2 | Setup: repo, branches, `.env`, Docker, Bob accounts | All 6 have a running local environment |
| 2–6 | **Contracts first.** `ARCHITECTURE.md` done. `agent_contracts.md` done. API skeleton with mock responses. | Both docs ✅ · API returning mock JSON ✅ |
| 6–16 | Everyone builds their component against the mock API. Each component passes its own unit tests in isolation. | Each component isolated and unit-tested |
| 16–24 | **First integration.** Wire orchestrator → backend → dashboard. Full pipeline runs once, even if ugly. | PLAN→BUILD→TEST(fail)→DEBUG→TEST(pass)→SEC(blocked)→FIX→SEC(pass)→APPROVAL→RELEASED |
| 24–32 | Fix wiring bugs. Polish integration. Fill Bob session files. Run pipeline 5× for stability. | Pipeline reliable. Bob session files non-empty. |
| 32–40 | Demo fixtures. Dashboard UI polish. Metrics panel. README. Diagrams. | `fixtures/*.json` committed. README readable by a stranger. |
| 40–48 | Demo rehearsal only. **Feature freeze at hour 40.** | Smooth 4-minute run, zero live LLM calls |

**Integration sync points:** H8 (stubs wired) · H16 (real agents running) · H24 (first full end-to-end, 30-min group session) · H32 (stable) · H40 (freeze)

---

## 15. Day 1 Task Plan

> Goal: every component built in isolation, one complete end-to-end pipeline run by hour 24.

---

### Leader — Orchestrator + AI

| Hours | Task | Output |
|---|---|---|
| H 0–2 | Set up repo, branches, Docker, Bob account. Share architecture doc with team. | Repo cloned by all, `docker-compose up`, `ARCHITECTURE.md` pushed |
| H 2–6 | Finalise `docs/ARCHITECTURE.md`. Scaffold `orchestrator/orchestrator.py`: state enum, transition table, gate stubs (all return PASS). Write `orchestrator/gates.py` with hardcoded pass criteria. | Orchestrator transitions through all states when agents are mocked |
| H 6–10 | Implement `orchestrator/runner.py`: parallel dispatch (call Tester + Security concurrently via asyncio), collect results, call `merge()`. | `runner.py` calls two stub agents in parallel and merges their `AgentResult` |
| H 10–14 | Wire orchestrator to Ali's API: replace in-memory state with HTTP calls to `/projects/{id}/start`, `/projects/{id}/status`, `/agents/results`. Write `tests/test_orchestrator.py`. | Orchestrator drives pipeline via backend API. Integration test green. |
| H 14–18 | Swap mock agent calls for real agent calls (Fati's plan_agent, Ali's builder, Manar's tester, Haytam's security). Run one full pipeline with stub data. | Pipeline completes PLAN → RELEASED with stub agents. Dashboard shows real state changes. |
| H 18–24 | First full integration run. Fix wiring bugs. Write `tests/test_gates.py`. Verify retry logic. Sync with Ali on API contract mismatches. | Pipeline runs end-to-end with planted failure and fix. All state transitions verified. |

---

### Ali — Full-Stack

| Hours | Task | Output |
|---|---|---|
| H 0–2 | Set up FastAPI project. Create `docker-compose.yml` (api + postgres). Create `.env.example`. | `docker-compose up` starts API on :8000, DB on :5432 |
| H 2–6 | Scaffold all 10 API endpoints returning hard-coded mock JSON. Create PostgreSQL schema: 5 tables. Write SQLAlchemy models. | All 10 endpoints return valid mock JSON. DB tables created. |
| H 6–10 | Replace mocks with real DB reads/writes for the three critical-path endpoints: `POST /projects`, `POST /projects/{id}/start`, `GET /projects/{id}/status`. | Leader can start and poll a project through the real API. |
| H 10–14 | Implement remaining 7 endpoints with real DB. Scaffold Next.js app. Create `PipelineView.tsx` (static layout). Add 3-second polling. | All endpoints backed by DB. Pipeline UI renders (static). |
| H 14–18 | Implement `builder_agent.py` stub. Connect `PipelineView.tsx` to polling. Each stage card reads from `GET /agents/results`. | Dashboard Pipeline View updates live as orchestrator transitions states. |
| H 18–24 | Wire `POST /projects/{id}/approve` to `ApprovalCard` component. Test full approval flow: orchestrator → AWAITING_APPROVAL → banner → Approve → RELEASED. Fix CORS/serialization issues. | Human approval flow works end-to-end from dashboard button to RELEASED state. |

---

### Fati — AI Agent Engineer

| Hours | Task | Output |
|---|---|---|
| H 0–2 | Read `ARCHITECTURE.md`. Set up Python environment. Create `agents/` folder structure. | Local environment ready |
| H 2–6 | Write `docs/agent_contracts.md`: full Pydantic schemas for all 5 objects. Push immediately — Manar and Haytam are blocked on this. | `agent_contracts.md` pushed and shared in team channel |
| H 6–10 | Implement `agents/plan_agent.py` stub: `run(input) → AgentResult`. Returns hard-coded demo requirements from `fixtures/plan_output.json`. Must pass the plan gate (≥5 user stories, stack named, ≥1 ADR). | Plan Agent stub returns valid AgentResult. Plan gate evaluates to PASS. |
| H 10–16 | Replace stub with a real Bob Plan mode session. Write `agents/prompts/plan.md`. Run the Bob session against the demo idea. Save output to `fixtures/plan_output.json`. | Real Plan Agent produces 6 user stories, PostgreSQL ADR, API list. Session saved to `bob_sessions/fati_plan_agent_session.md`. |
| H 16–24 | Validate Plan Agent output against gate criteria with Leader. Fix gaps. Help Leader wire `plan_agent` into the orchestrator. Write `tests/test_agents.py::test_plan_agent_output_passes_gate`. | Plan Agent integrated. Unit test green. |

---

### Manar — QA / Testing

| Hours | Task | Output |
|---|---|---|
| H 0–6 | Wait for Fati's `agent_contracts.md` (ready by H6). Design the 20-test suite for the demo milestone. Decide which 3 will fail (DELETE /tasks/{id} ownership checks). Create fixtures manually. | `fixtures/test_fail_17_20.json` and `fixtures/test_pass_20_20.json` committed |
| H 6–10 | Implement `agents/tester_agent.py` stub: returns `test_fail_17_20.json` on first call, `test_pass_20_20.json` on subsequent calls. | Tester stub called by orchestrator. DEBUGGING state fires correctly after first call. |
| H 10–16 | Implement `agents/debugger_agent.py`: returns hard-coded root cause + fake patch diff. Write `agents/prompts/debugger.md`. Verify TESTING → DEBUGGING → TESTING → PASS loop. | Debug loop works end-to-end with stubs. |
| H 16–24 | Replace Debugger stub with a real Bob Agent mode session. Write Bob prompt that takes failing test JSON + file content, returns root cause + patch. Run against planted failure. Save to `bob_sessions/manar_debugger_session.md`. | Real Debugger Agent produces root cause + patch for the ownership bug. Session file saved. |

---

### Haytam — Cybersecurity

| Hours | Task | Output |
|---|---|---|
| H 0–6 | Wait for Fati's `agent_contracts.md` (ready by H6). Design planted vulnerability: broken access control on DELETE /tasks/{id}, CWE-639. Write SecurityFinding JSON manually. Create both fixture files. | `fixtures/security_finding_HIGH.json` and `fixtures/security_pass.json` committed |
| H 6–10 | Implement `security/security_agent.py` stub: first call returns BLOCKED, second returns PASS. Implement `security/gate.py`: evaluates severity counts, returns GateResult. | Security gate fires BLOCKED on first call, PASS on second. SECURITY_FIX state confirmed. |
| H 10–16 | Implement `security/scanner.py`: Bandit wrapper. Map Bandit severity to SecurityFinding.severity. Write unit test that Bandit finds the planted vulnerability. | Scanner finds CWE-639 in `backend/routers/tasks.py`. Unit test green. |
| H 16–24 | Replace security stub with real Bob Agent mode + Bandit pipeline. Write `prompts/security.md`. Run against demo code. Save to `bob_sessions/haytam_security_session.md`. Coordinate with Manar on shared PASS/FAIL/FINDING format. | Real Security Agent returns SecurityFinding[]. Shared format with Manar verified. |

---

### Safa — Memory + Metrics

| Hours | Task | Output |
|---|---|---|
| H 0–4 | Coordinate with Ali on `decisions` and `gate_results` table schema. Define Pydantic models in `memory/schemas.py`. | `memory/schemas.py` committed. DB tables agreed with Ali. |
| H 4–10 | Implement `memory/memory_agent.py`: `store(decision)` writes to DB (async). `query(project_id, topic)` returns top 3 decisions by keyword. `get_context(project_id)` returns formatted string of all decisions. | Memory agent stores and retrieves decisions. Unit test green. |
| H 10–16 | Implement `memory/metrics.py`: 8 counters (total_time, tests_run, tests_passed, bugs_found, bugs_fixed, vulns_found, vulns_fixed, retry_count, human_interventions). Updated by AgentResult events from orchestrator. | Metrics update correctly. `GET /metrics` returns real numbers. |
| H 16–24 | Wire Memory Agent into orchestrator: after each gate result and Plan Agent decision, call `memory_agent.store()`. Verify Decision Log screen shows real entries. Save Bob session. | Decision log on dashboard shows real decisions from the pipeline run. Bob session saved. |

---

## 16. Day 2 Task Plan

> Goal: reliable pipeline, demo-polished UI, feature freeze at H40, rehearse until H48.

> **Hour 24 sync (mandatory, 30 min):** Every member demos their component. Leader runs the pipeline live. Identify top 3 blocking bugs. Assign fixes before sync ends.

---

### Leader — Orchestrator + AI

| Hours | Task | Output |
|---|---|---|
| H 24–28 | Fix top bugs from H24 sync. Run pipeline 3× with real agents. Confirm retry counters increment correctly. Confirm both HUMAN_REVIEW escalations (test retry=3, security retry=2) work. | Pipeline runs 3× without crashing. Escalation paths tested. |
| H 28–32 | Create all demo fixture files. Run pipeline once in "demo mode" (reads fixtures instead of calling agents live). Confirm full pipeline completes in under 60 seconds. | Demo mode pipeline completes <60 s. All fixtures committed. |
| H 32–36 | Final code review using Bob Agent mode: review `orchestrator/`, `agents/`, `security/`, `memory/` for bugs, hardcoded values, missing error handling. Save to `bob_sessions/leader_orchestrator_session.md`. | Code review session saved. Critical findings fixed. |
| H 36–40 | Write `README.md`. Draw architecture diagram (pipeline + state machine), add to `docs/`. Verify all `bob_sessions/` files are non-empty. **Feature freeze.** | README done. Diagram in docs/. All bob_sessions populated. Freeze confirmed. |
| H 40–48 | Demo rehearsal only. Run 4-minute script 4× with full team. Assign who speaks at each step. No new code. | Team delivers clean 4-minute demo with no fumbles. |

---

### Ali — Full-Stack

| Hours | Task | Output |
|---|---|---|
| H 24–28 | Fix API bugs from H24 sync. Ensure all 10 endpoints return correctly typed responses matching Pydantic schemas. Add CORS headers if missing. | All 10 endpoints return valid JSON matching `agent_contracts.md`. |
| H 28–32 | Polish `PipelineView.tsx`: stage cards animate between states (CSS transitions). Expand/collapse test failure and security finding cards. Add retry count badge. Make "Waiting for Human" banner prominent. | Pipeline View is demo-ready. State transitions visually smooth. |
| H 32–36 | Build `ApprovalCard.tsx`: gate summary, milestone statuses, coverage %, security posture, decision count, changelog. Wire Approve / Request Changes buttons. Build `decisions/page.tsx` with Impact metrics panel. | Both approval screens work. Metrics panel shows real numbers from Safa's API. |
| H 36–40 | End-to-end UI test with full demo script. Fix display bugs. Save Bob builder session evidence. **Feature freeze at H40.** | Dashboard runs full 4-minute demo without visual errors. Bob session saved. |
| H 40–48 | Demo rehearsal: control the browser. No new code unless a rehearsal-breaking defect is found. | Dashboard performs cleanly in every rehearsal run. |

---

### Fati — AI Agent Engineer

| Hours | Task | Output |
|---|---|---|
| H 24–28 | Run Plan Agent 3× against the demo idea. Confirm output always passes the plan gate. Fix prompt if it fails. Freeze best output as `fixtures/plan_output.json`. | Plan Agent output is deterministic and gate-passing. Fixture frozen. |
| H 28–32 | Verify Memory Agent stores Plan Agent decisions correctly (Safa integration). Confirm the architecture ADR appears in the Decision Log on the dashboard. | ADR and tech-stack decisions appear in Decision Log screen. |
| H 32–36 | Finalise `docs/agent_contracts.md` with any schema changes found during integration. Ensure all 5 Pydantic models match what agents produce and what the backend stores. | `agent_contracts.md` is accurate and final. No schema mismatches. |
| H 36–40 | Complete Bob session evidence: `bob_sessions/fati_plan_agent_session.md` with full prompt, output, and ADR decision note. Prepare to narrate the PLAN step. | Bob session file complete. Fati ready to explain the planning phase. |
| H 40–48 | Demo rehearsal. Speak during "research and plan" step. Answer judge questions about the requirements agent, Bob Plan mode, agent contracts. | Confident, clear explanation of the planning phase. |

---

### Manar — QA / Testing

| Hours | Task | Output |
|---|---|---|
| H 24–28 | Replace Tester Agent stub with a real Bob Agent mode session. Write `prompts/tester.md`. Run against demo code. Confirm output matches TestResult schema and produces 17/20 on first run. | Real Tester Agent produces 17/20. Session saved. |
| H 28–32 | Verify Debugger → Tester loop with real agents: planted bug → Tester 17/20 → Debugger patch → Tester 20/20. Confirm all 3 AgentResult records in DB. Confirm retry counter = 1 on dashboard. | Full debug loop runs reliably. Retry counter visible on dashboard. |
| H 32–36 | Add regression test: after security fix, re-run Tester to confirm no new failures introduced. Wire into SECURITY_FIX → TESTING transition. Confirm 20/20 still passes after security patch. | Regression test in security fix loop works. No false failures. |
| H 36–40 | Save Bob session evidence for both Tester and Debugger. Write `test_orchestrator.py::test_debug_loop_max_3_escalates`. | Both Bob sessions saved. Escalation test green. |
| H 40–48 | Demo rehearsal. Speak during "test fails / debug / fix" steps. Explain the debug loop, root cause, and retry counter to judges. | Confident explanation of testing and debugging phases. |

---

### Haytam — Cybersecurity

| Hours | Task | Output |
|---|---|---|
| H 24–28 | Replace Security Agent stub with real Bob Agent mode + Bandit pipeline. Run against demo code with planted vulnerability. Confirm SecurityFinding severity=HIGH, cwe=CWE-639, file=tasks.py:54. Gate evaluates to BLOCKED. | Real Security Agent returns the planted HIGH finding. Gate BLOCKED confirmed. |
| H 28–32 | Test the full security fix loop: BLOCKED → Builder patches `tasks.py:54` → Security reruns → PASS. Confirm finding status = FIXED in DB. Dashboard Security stage shows ✅. | Security fix loop runs end-to-end. Finding = FIXED. Dashboard updated. |
| H 32–36 | Prepare the demo vulnerability narrative: one-paragraph explanation of CWE-639, why it is dangerous, how DevForge caught it automatically. Practice in under 20 seconds. Coordinate with Manar: same file, same line, different tool. | Vulnerability narrative scripted. Coordination with Manar confirmed. |
| H 36–40 | Complete Bob session evidence: `bob_sessions/haytam_security_session.md`. Test max-retry escalation path (force 2 failed fix attempts → HUMAN_REVIEW fires). | Bob session saved. Escalation path tested. |
| H 40–48 | Demo rehearsal. Speak during "security finds vulnerability / fix" steps. Explain CWE-639, the automated fix, why the gate blocked release. | Confident, concise explanation of the security phase. |

---

### Safa — Memory + Metrics

| Hours | Task | Output |
|---|---|---|
| H 24–28 | Run full pipeline and verify all 8 metrics counters update correctly. Fix any events the orchestrator is not yet calling `memory_agent.store()` for. | All 8 metrics are correct after a full pipeline run. |
| H 28–32 | Wire `GET /metrics` to Ali's DevForge Impact panel. Confirm panel shows: "1 bug auto-fixed, 1 vulnerability auto-patched, 2 retries, 2 human interventions" after the full demo run. Must be real DB values, not hardcoded strings. | Impact panel shows accurate real numbers from the pipeline run. |
| H 32–36 | Implement context injection: `memory_agent.get_context(project_id)` formats the top 5 decisions as a prompt prefix. Test that Builder on milestone 2 receives the PostgreSQL ADR decision in its context. Save Bob session evidence. | Context injection works. Builder receives prior decisions in prompt. Bob session saved. |
| H 36–40 | Prepare Decision Log screen for the demo: ensure 7–8 decisions from the pipeline appear with correct source (agent name) and timestamp. Confirm the screen looks presentable. | Decision Log shows 7+ real decisions. Looks presentable. |
| H 40–48 | Demo rehearsal. Speak during the closing "DevForge Impact" section. Present the metrics panel and explain what each number means. Answer judge questions about decision memory. | Clear, compelling explanation of memory and metrics value. |

---

## 17. Simplifications Summary

| Removed | Why |
|---|---|
| 14 agents → 6 agents | Each removed agent was a duplicate, a single LLM call inside another, or not in the demo narrative |
| Separate Fix Agent | Builder + a finding as input = a fix. No new component needed. |
| Vector search on memory | ~10 decisions fit in SQL `WHERE project_id = ?`. Vector search is a 2-day side project. |
| Real-time WebSocket | 3-second polling is invisible to the audience. WebSocket adds infrastructure risk. |
| 5 human approval points → 2 | Two approvals tell the story cleanly. More slow the demo and add UI complexity. |
| Performance / SEO agents | Not demoed. Stub returns PASS if the gate exists in code; skip otherwise. |
| Live LLM calls during demo | Pre-recorded fixtures make the demo deterministic. The pipeline is real; LLM outputs are pre-validated. |
| 9 dashboard screens → 3 | Pipeline View is the demo. The rest is supporting detail. |

---

## 18. Demo Script

> The demo replays pre-recorded fixtures through the real orchestrator and real dashboard.
> Zero live LLM calls. Presenter controls the browser.

| Time | What the presenter says | Screen shows | Speaker |
|---|---|---|---|
| 0:00 | "Here is our idea: a task-management SaaS for small teams." | Developer types idea. Pipeline starts. Status = PLANNING. | Leader |
| 0:15 | "The Plan Agent researches and produces requirements and an architecture." | ✅ PLAN — 6 user stories, PostgreSQL ADR, API list. Gate PASS. | Fati |
| 0:45 | "We review and approve the architecture." | Approval Card shown. Presenter clicks Approve. | Leader |
| 1:05 | "The Builder generates Milestone 1: the Task CRUD API." | ✅ BUILD — code files listed. | Ali |
| 1:25 | "The Tester and Security Agent run in parallel." | Both stage cards animate to IN PROGRESS simultaneously. | Leader |
| 1:45 | "The test fails. 17 out of 20 pass. Three ownership checks are broken." | 🔴 TEST 17/20 — failure detail expands. | Manar |
| 2:05 | "The Debugger finds the root cause and patches the ownership check." | ⚙ DEBUG — root cause shown. Patch applied. | Manar |
| 2:20 | "20 out of 20. Tests pass." | ✅ TEST 20/20. Retry count = 1 visible. | Manar |
| 2:35 | "The Security Agent flagged a HIGH vulnerability: broken access control on the delete endpoint." | 🔴 SECURITY — finding card: CWE-639, tasks.py:54. Gate BLOCKED. | Haytam |
| 2:55 | "The Builder patches it. Security rescans. Clean." | ✅ SECURITY — zero CRITICAL/HIGH. Finding = FIXED. | Haytam |
| 3:15 | "All gates passed. Milestone 1 approved." | Milestone APPROVED. Impact panel updates. | Leader |
| 3:30 | "Human approves the release." | Release approval card. Presenter clicks Approve. Status → RELEASED. | Leader |
| 3:50 | "DevForge: one idea — planned, built, tested, secured, released — with two human decisions." | Impact panel: 1 bug auto-fixed, 1 vuln auto-patched, 2 retries, 2 human actions. | Safa |

---

## Core Principles

- **Single state owner.** Only the orchestrator writes `project.status`. Agents are stateless workers.
- **Typed contracts everywhere.** Every agent boundary is one of 5 JSON objects. No free-form text between components.
- **Fail fast, fix locally.** Every gate failure triggers the nearest fix loop. Humans only see problems agents cannot solve within retry limits.
- **Demo resilience.** Pre-recorded fixtures, real orchestrator, real dashboard. LLM outputs are pre-validated before the presentation.
- **Bob is substantive, not cosmetic.** Plan mode, Agent mode, parallel subagents, context injection — each with a session file as evidence.

---

*Document version: 1.0 — Final MVP*  
*Authors: Leader (Technical Architect), DevForge team*
