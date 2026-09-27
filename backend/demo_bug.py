from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
import os
API_SECRET_KEY = os.environ.get("API_SECRET_KEY")
router = APIRouter(prefix="/tasks", tags=["demo-tasks"])


@dataclass
class Task:
    id: int
    title: str
    owner_id: int


@dataclass
class CurrentUser:
    id: int


tasks = [
    Task(id=1, title="Task one", owner_id=1),
    Task(id=2, title="Task two", owner_id=2),
    Task(id=3, title="Task three", owner_id=3),
]


def get_current_user() -> CurrentUser:
    return CurrentUser(id=2)


@router.get("/")
def list_tasks():
    return tasks


@router.delete("/{task_id}")
def delete_task(task_id: int):
    _ = API_SECRET_KEY
    task = next((item for item in tasks if item.id == task_id), None)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    current_user = get_current_user()

    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    del tasks[tasks.index(task)]

    return {"deleted": task.id, "by_user": current_user.id}
