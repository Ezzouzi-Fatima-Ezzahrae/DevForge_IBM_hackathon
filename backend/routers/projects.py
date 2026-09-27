from pathlib import Path
import io
import json
import os
import time
import uuid
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.runs import start_run, is_running
from orchestrator import agents_base
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


def _is_real_agent(stage: str) -> bool:
    """Whether the currently-registered agent for *stage* is a real
    implementation rather than one of the orchestrator.stubs.* placeholders.
    Read from the live registry instead of a hardcoded set so this badge
    can't silently drift out of sync with orchestrator/agents_base.py again."""
    try:
        agent = agents_base.get_agent(stage)
    except KeyError:
        return False
    return "Stub" not in type(agent).__name__


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
            "real": _is_real_agent(name) if name in {"plan", "build", "test", "debug", "security", "fix"} else True,
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


def _agent_summary(events: list[dict], stage: str) -> str | None:
    """Last AGENT_DONE summary logged for *stage*, or None if it never ran."""
    summary = None
    for event in events:
        if event.get("event") == "AGENT_DONE" and event.get("stage") == stage:
            summary = event.get("summary")
    return summary


def _build_readme(project_id: str, state: dict, events: list[dict]) -> str:
    idea = state.get("idea", "")
    test_summary = _agent_summary(events, "test") or "not run"
    debug_summary = _agent_summary(events, "debug")
    security_summary = _agent_summary(events, "security") or "not run"
    fix_summary = _agent_summary(events, "fix")
    retries = state.get("retries", {})
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# {idea or 'DevForge project'}",
        "",
        f"Generated by DevForge — project `{project_id}`, released {generated_at}.",
        "",
        "## What's in this package",
        "",
        "`tasks_api.py` is the real, working Task API source file from this run — the same",
        "file DevForge's Test, Debug, Security and Fix agents ran against, patched and",
        "re-verified. It is not a scaffold or a mockup: every check below ran against this",
        "exact code.",
        "",
        "## Quality gates this code passed",
        "",
        f"- **Tests:** {test_summary} (retries: {retries.get('test', 0)})",
    ]
    if debug_summary:
        lines.append(f"- **Debug:** {debug_summary}")
    lines.append(f"- **Security:** {security_summary} (retries: {retries.get('security', 0)})")
    if fix_summary:
        lines.append(f"- **Fix:** {fix_summary}")
    lines += [
        "",
        "## Honesty note",
        "",
        "DevForge's Build agent is still a stub today — this package is the real demo API,",
        "not a freshly AI-generated app. What's real is everything downstream of it: the",
        "tests that ran, the vulnerability that was found and the patch that fixed it. See",
        "the Audit Trail in the DevForge dashboard for the full, timestamped record of every",
        "decision on this run.",
        "",
        "## Run it",
        "",
        "```",
        "pip install fastapi uvicorn",
        "uvicorn tasks_api:router  # or mount it in your own FastAPI app",
        "```",
    ]
    return "\n".join(lines) + "\n"


@router.get("/{project_id}/download")
def download_project(project_id: str):
    state = _load_state()

    if state.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    if state.get("status") != "RELEASED":
        raise HTTPException(status_code=409, detail="Project has not been released yet")

    source = Path("backend/demo_bug.py")
    if not source.exists():
        raise HTTPException(status_code=500, detail="Released source file is missing")

    events = _load_events(project_id)
    readme = _build_readme(project_id, state, events)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tasks_api.py", source.read_text(encoding="utf-8"))
        zf.writestr("README.md", readme)
    buffer.seek(0)

    filename = f"devforge-{project_id}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
