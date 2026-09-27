from pathlib import Path
import json
import os
import time
import uuid
import subprocess
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.runs import start_run, is_running
from orchestrator.approval_broker import broker


router = APIRouter(prefix="/projects", tags=["projects"])

STATE_FILE = Path("data/project_state.json")
LOG_FILE = Path("logs/orchestrator.jsonl")


class ProjectCreate(BaseModel):
    idea: str


class ApprovalRequest(BaseModel):
    gate: str
    approved: bool


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}

    # The pipeline rewrites this file at every step: retry if we read it half-written.
    for _ in range(5):
        try:
            with STATE_FILE.open(encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            time.sleep(0.05)
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with STATE_FILE.open("w") as f:
        json.dump(state, f, indent=2)


def _load_events(project_id: str) -> list[dict]:
    if not LOG_FILE.exists():
        return []

    events = []

    with LOG_FILE.open() as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("project_id") == project_id:
                events.append(event)

    return events


def _build_stages(events: list[dict]) -> list[dict]:
    stage_names = [
        "plan",
        "build",
        "test",
        "debug",
        "security",
        "fix",
        "approval",
        "release",
    ]

    stages = {
        name: {
            "name": name,
            "state": "pending",
            "verdict": None,
            "summary": "",
            "duration_seconds": 0.0,
            "real": name not in {"build", "fix"},
        }
        for name in stage_names
    }

    for event in events:
        stage = event.get("stage")

        if event.get("event") == "AGENT_START" and stage in stages:
            stages[stage]["state"] = "running"

        elif event.get("event") == "AGENT_DONE" and stage in stages:
            stages[stage]["state"] = (
                "done" if event.get("status") == "PASS" else "failed"
            )
            stages[stage]["verdict"] = event.get("status")
            stages[stage]["summary"] = event.get("summary", "")
            stages[stage]["duration_seconds"] = event.get(
                "duration_seconds", 0.0
            )

        elif event.get("event") == "HUMAN_APPROVAL":
            if event.get("gate") == "release":
                stages["approval"]["state"] = "done"
                stages["approval"]["verdict"] = (
                    "PASS" if event.get("approved") else "FAIL"
                )
                stages["approval"]["summary"] = (
                    "Release approved by human"
                    if event.get("approved")
                    else "Release rejected by human"
                )

        elif event.get("event") == "STATE_TRANSITION":
            if event.get("to") == "RELEASED":
                stages["release"]["state"] = "done"
                stages["release"]["verdict"] = "PASS"
                stages["release"]["summary"] = "Project released"

    return list(stages.values())


def _restore_demo_bug() -> None:
    try:
        subprocess.run([sys.executable, "tests/restore_demo_bug.py"], check=True,
                       stdout=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError) as exc:
        raise HTTPException(status_code=500, detail="Failed to restore demo bug") from exc


@router.post("")
def create_project(payload: ProjectCreate):
    project_id = f"proj_{uuid.uuid4().hex[:8]}"

    state = {
        "project_id": project_id,
        "idea": payload.idea,
        "status": "IDLE",
        "current_milestone_index": 0,
        "milestones": [],
        "retries": {"plan": 0, "test": 0, "security": 0},
        "human_approved_arch": False,
        "human_approved_release": False,
    }

    _save_state(state)

    return {"project_id": project_id}


@router.post("/{project_id}/start")
def start_project(project_id: str):
    state = _load_state()

    if state.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    if is_running(project_id):
        return {"status": "started"}

    # The real debug agent patches backend/demo_bug.py: put the planted bug back
    # so every demo run starts from the same broken code.
    if os.environ.get("DEVFORGE_TEST_AGENT_MODE", "real") != "stub":
        _restore_demo_bug()

    if not start_run(project_id, state["idea"]):
        raise HTTPException(
            status_code=409,
            detail="Project is already running",
        )

    return {"status": "started"}


@router.get("/{project_id}/status")
def project_status(project_id: str):
    state = _load_state()

    if state.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    events = _load_events(project_id)

    return {
        "project_id": project_id,
        "idea": state.get("idea", ""),
        "status": state.get("status", "IDLE"),
        "retries": state.get("retries", {}),
        "running": is_running(project_id),
        "stages": _build_stages(events),
        "awaiting_approval": broker.pending(project_id),
        "events": events,
    }


@router.post("/{project_id}/approve")
def approve_project(project_id: str, payload: ApprovalRequest):
    state = _load_state()

    if state.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.gate not in {"architecture", "release"}:
        raise HTTPException(status_code=400, detail="Invalid gate")

    pending = broker.pending(project_id)
    if pending is not None and pending["gate"] != payload.gate:
        raise HTTPException(
            status_code=409,
            detail=f"The pending approval is for the {pending['gate']} gate",
        )

    if not broker.resolve(project_id, payload.approved):
        raise HTTPException(
            status_code=409,
            detail="No approval request is pending",
        )

    return {"status": "ok"}


@router.post("/{project_id}/reset")
def reset_project(project_id: str):
    state = _load_state()

    if state.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    if is_running(project_id):
        raise HTTPException(
            status_code=409,
            detail="Project is still running",
        )

    try:
        subprocess.run(
            [sys.executable, "tests/restore_demo_bug.py"],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to restore demo bug",
        ) from exc

    return {"status": "ok"}