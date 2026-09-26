# Haytam — Security Lead

## Role
Security lead. Make security a real quality gate, not a checkbox.

## Branch and Folder
- **Branch:** `haytam/security`
- **Folder:** `security/`

---

## Objective
Build a Security Red-Team Agent that actively attacks the generated code, reports findings by severity, and blocks the pipeline if any critical or high issue is found. Prove it works by detecting a vulnerability you plant yourself.

---

## Context
DevForge orchestrates: **Idea → Research → Requirements → Architecture → Milestones → Build → Test → Debug → Security → Human Approval → Release**.
The Security Agent runs after every milestone is built and tested. It is a hard gate: if it returns `BLOCKED`, the pipeline stops until the finding is fixed.
Demo app: a simple task-management SaaS (FastAPI backend). Stack: FastAPI + PostgreSQL + Next.js. Do not expand the stack.

Every agent returns:
```json
{ "agent": "...", "status": "PASS | FAIL | ERROR", "summary": "...", "data": {}, "duration_seconds": 0, "timestamp": "..." }
```

---

## Deliverables

- [ ] **Security Red-Team Agent** (`security/security_agent.py`) that analyzes code for:
  - Authentication and authorization flaws
  - Input validation and sanitization gaps
  - API security issues (missing rate limiting, exposed internals)
  - Hardcoded secrets or exposed credentials
  - Vulnerable dependencies
  - SQL injection, XSS, CSRF
  - Misconfigured settings (debug mode on, open CORS, etc.)
- [ ] **Findings report** with severity counts and a pipeline verdict:
  - `PASS` — zero critical, zero high findings
  - `BLOCKED` — one or more critical or high findings
- [ ] **Fix-and-retest loop:** Finding → developer fixes → agent rescans → `PASS`
- [ ] **One intentional vulnerability** planted in the demo app for the live demo (recommended: missing ownership check on a tasks endpoint — a user can delete another user's task). The agent must detect it and `BLOCK` the pipeline.
- [ ] **Bob evidence:** `bob_sessions/haytam_task01_security.png`

### Finding JSON shape
```json
{
  "id": "SEC-001",
  "severity": "critical | high | medium | low",
  "type": "broken_access_control | injection | secrets_exposure | ...",
  "location": "backend/routers/tasks.py:54",
  "description": "DELETE /tasks/{id} does not verify task ownership",
  "recommended_fix": "Check that request.user.id == task.owner_id before deleting"
}
```

The `data` field of `AgentResult` must contain `{ "findings": [...], "verdict": "PASS | BLOCKED", "counts": { "critical": 0, "high": 1, "medium": 2, "low": 3 } }`.

---

## Dependencies

| Depends on | What you need |
|---|---|
| **Manar** | Agree on the shared `PASS/FAIL/FINDING/SEVERITY/FIX/RETEST` format before hour 4. Security runs _after_ tests pass. |
| **Leader** | Gate rules: BLOCKED threshold, retry limit (max 2 fix attempts before human escalation) |
| **Ali** | `GET /security` endpoint must match your FindingResult shape exactly |

---

## Bob Task
Use **Bob Agent mode** to design and implement the Security Agent and the vulnerability scan logic.
1. Run the prompt below.
2. Screenshot the Bob session → save as `bob_sessions/haytam_task01_security.png`.

---

## Definition of Done
- [ ] `security_agent.py` runs against the demo app code and returns a valid `AgentResult` JSON.
- [ ] The planted vulnerability is detected with `severity: "high"` and verdict `BLOCKED`.
- [ ] After a fix is applied, the agent rescans and returns verdict `PASS`.
- [ ] Bob session screenshot saved in `bob_sessions/`.

---

## Deadline — First Sync (~hour 4)
Have the agent stub running and returning mock JSON. The planted vulnerability file must exist. Share your screen at the sync and confirm the shared finding format with Manar.

---

## Bob Prompt

```
You are an expert Python security engineer and application security analyst.

CONTEXT
Project: DevForge — an AI Software Development Lifecycle Orchestrator.
You are building the Security Red-Team Agent for DevForge.
The agent scans FastAPI + PostgreSQL backend code after each milestone build.
Demo app being scanned: a simple task-management SaaS (FastAPI backend).
Stack: FastAPI, PostgreSQL, Python 3.11. Do not add other tools.

TASK
1. Create security/security_agent.py with a class SecurityAgent that has:
   - run(code_files: list[str]) -> dict
     Scans all given file paths for security issues and returns an AgentResult:
     { "agent": "security_agent", "status": "PASS | FAIL | ERROR",
       "summary": "...", "data": { "findings": [...], "verdict": "PASS | BLOCKED",
       "counts": { "critical": 0, "high": 0, "medium": 0, "low": 0 } },
       "duration_seconds": 0, "timestamp": "..." }
   - The verdict is BLOCKED if counts.critical > 0 or counts.high > 0.

2. Each finding must match:
   { "id": "SEC-NNN", "severity": "critical|high|medium|low",
     "type": "broken_access_control | injection | secrets_exposure | misconfiguration | ...",
     "location": "file:line", "description": "...", "recommended_fix": "..." }

3. Implement checks for:
   - Missing ownership verification on resource mutation endpoints (broken access control)
   - SQL injection risk (string-formatted queries)
   - Hardcoded secrets (regex scan for API_KEY, PASSWORD, SECRET patterns)
   - Debug mode enabled in config
   - Missing input validation (no Pydantic model on request body)

4. Create security/scanner.py with helper functions used by the agent.

5. Create tests/fixtures/security_finding_HIGH.json — a pre-recorded AgentResult
   where one HIGH finding is present (verdict BLOCKED). Use the broken_access_control type.

6. Create tests/fixtures/security_pass.json — a pre-recorded AgentResult
   with zero findings (verdict PASS).

CONSTRAINTS
- Pure Python, no external security scanning tools.
- All findings are produced by static analysis of source code (read file contents, apply regex and AST checks).
- The agent must be importable as: from security.security_agent import SecurityAgent

OUTPUT FORMAT
File tree first, then each file in full.
```
