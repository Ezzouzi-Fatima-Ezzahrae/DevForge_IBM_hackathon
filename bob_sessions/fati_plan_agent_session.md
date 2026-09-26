# Bob session: Fati — Plan Agent (Plan mode)

## Demo idea

task-management SaaS for small teams

## Reference files

- docs/ARCHITECTURE.md
- docs/agent_contracts.md
- agents/prompts/plan.md

## Task

Generate the real Plan Agent output in Bob Plan mode.

The Plan Agent combines:
- Research
- Requirements
- Architecture

## Bob Plan output

Bob generated:

- 6 user stories
- Acceptance criteria for each story
- Full-stack architecture
- 9 API endpoints
- PostgreSQL architecture decision
- JWT authentication decision
- Frontend architecture decision

## User stories

1. REQ-001 — User registration and login
2. REQ-002 — Create a task
3. REQ-003 — View tasks
4. REQ-004 — Update a task
5. REQ-005 — Delete a task
6. REQ-006 — Share a task with another user

Each user story contains acceptance criteria.

## Architecture

Frontend:
Next.js 14 with TypeScript and Tailwind CSS

Backend:
FastAPI with Python 3.11 and SQLAlchemy 2.0

Database:
PostgreSQL 15

Authentication:
JWT

Infrastructure:
Docker Compose

## APIs

- POST /auth/register
- POST /auth/login
- POST /tasks
- GET /tasks
- GET /tasks/{id}
- PATCH /tasks/{id}
- DELETE /tasks/{id}
- POST /tasks/{id}/share
- GET /health

## Architecture decisions

ADR-001: PostgreSQL as the primary database.

ADR-002: JWT for authentication.

ADR-003: Next.js with TypeScript and Tailwind CSS for the frontend.

## Plan Gate check

- 6 user stories: PASS
- Each story has acceptance criteria: PASS
- Technology stack named: PASS
- PostgreSQL ADR present: PASS

## Result

The Bob Plan session produced a valid Plan Agent plan satisfying the required Plan Gate criteria.
