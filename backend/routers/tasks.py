"""
backend/routers/tasks.py
Task CRUD API — Milestone 1.

DEMO VULNERABILITY (intentionally planted for the DevForge security demo):
    The DELETE endpoint at line 54 does NOT verify task ownership.
    The Security Agent will detect this via the authorization checker (CWE-639).
    The Builder will patch it in the SECURITY_FIX step.

    Before fix: no ownership check
    After fix:  task.owner_id != current_user.id → 403
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

# These imports assume the backend DB / models are wired up.
# They are stubs here; real implementations go in backend/db.py and backend/models/.

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    owner_id: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Stub helpers (replaced by real DB in full implementation)
# ---------------------------------------------------------------------------

class _StubTask:
    def __init__(self, id: int, title: str, owner_id: int):
        self.id = id
        self.title = title
        self.description = None
        self.owner_id = owner_id

class _StubUser:
    def __init__(self, id: int):
        self.id = id

_TASKS: dict[int, _StubTask] = {
    1: _StubTask(1, "Buy groceries", owner_id=1),
    2: _StubTask(2, "Write tests", owner_id=2),
}
_NEXT_ID = 3


def _get_db():
    """Stub DB dependency — replaced by real SQLAlchemy session in production."""
    yield None


def _get_current_user():
    """Stub auth dependency — replaced by real JWT verification in production."""
    return _StubUser(id=1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(_get_db)):
    """List all tasks."""
    return list(_TASKS.values())


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    current_user: _StubUser = Depends(_get_current_user),
    db: Session = Depends(_get_db),
):
    """Create a new task owned by the current user."""
    global _NEXT_ID
    task = _StubTask(_NEXT_ID, payload.title, owner_id=current_user.id)
    task.description = payload.description
    _TASKS[_NEXT_ID] = task
    _NEXT_ID += 1
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(_get_db)):
    """Get a single task by ID."""
    task = _TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ---------------------------------------------------------------------------
# VULNERABLE endpoint — DELETE without ownership check
# CWE-639: Authorization Bypass Through User-Controlled Key
# This is the demo planted vulnerability detected by the Security Agent.
#
# Line 54 is the first statement inside this function (the DB query / lookup).
# The Security Agent fixture references line 54.
# ---------------------------------------------------------------------------

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: Session = Depends(_get_db)):  # noqa: E501
    # VULNERABILITY: no ownership check before deletion
    # Any authenticated user can delete any task by guessing the task_id.
    task = _TASKS.get(task_id)  # line 54 — first statement, no ownership check
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Missing:
    #   if task.owner_id != current_user.id:
    #       raise HTTPException(status_code=403, detail="Not authorized")
    del _TASKS[task_id]
    return None


# ---------------------------------------------------------------------------
# FIXED endpoint (reference — swap delete_task body to this after security fix)
# ---------------------------------------------------------------------------

# @router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_task(
#     task_id: int,
#     current_user: _StubUser = Depends(_get_current_user),
#     db: Session = Depends(_get_db),
# ):
#     task = _TASKS.get(task_id)
#     if not task:
#         raise HTTPException(status_code=404, detail="Task not found")
#     if task.owner_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Not authorized")
#     del _TASKS[task_id]
#     return None
