"""
memory/log_ingest.py

Reads logs/orchestrator.jsonl (produced by the orchestrator run) and feeds:
  - metrics.record_event(...)   -> time-based metrics, retries, human approvals,
                                    test pass/fail counts, security findings
  - memory_agent.store(...)     -> plan-stage decisions (ADRs), when the log
                                    carries structured decision data

Run once after each pipeline execution:
    python -m memory.log_ingest
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from memory import metrics
from memory import memory_agent

LOG_FILE = Path(__file__).parent.parent / "logs" / "orchestrator.jsonl"


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _load_events() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _time_in_state(transitions: list[dict], *state_names: str) -> float:
    """Sum the seconds spent in any of *state_names*, using STATE_TRANSITION
    events' timestamps (entering vs leaving the state)."""
    total = 0.0
    for i, t in enumerate(transitions):
        if t["from"] in state_names:
            leave_ts = _parse_ts(t["ts"])
            entered = next(
                (p for p in reversed(transitions[:i]) if p["to"] == t["from"]),
                None,
            )
            if entered:
                total += (leave_ts - _parse_ts(entered["ts"])).total_seconds()
    return round(total, 3)


def _run_id_for(events: list[dict]) -> str:
    """Derive a stable fingerprint for a set of log events.

    Built from the sorted JSON of every event's (ts, event, project_id) triple
    so that the same logical run always produces the same run_id regardless of
    file position or wall-clock time.
    """
    fingerprint = json.dumps(
        sorted(
            (e.get("ts", ""), e.get("event", ""), e.get("project_id", ""))
            for e in events
        ),
        sort_keys=True,
    )
    return hashlib.sha1(fingerprint.encode()).hexdigest()


def ingest(project_id: str | None = None) -> dict:
    """Parse the log once, record every metric event, return the resulting
    summary for the project.

    This function is **idempotent**: calling it a second time with the same
    log file and project_id returns the already-stored summary without
    appending duplicate metric events.  Idempotency is guaranteed via a
    content-based ``run_id`` fingerprint stored on every metric event.

    If *project_id* is not given, it defaults to the project_id of the last
    event in the file (i.e. the most recent run).  Only events belonging to
    that project_id are processed, so runs are never mixed together.
    """
    all_events = _load_events()
    if not all_events:
        return {}

    if project_id is None:
        project_id = all_events[-1]["project_id"]
    assert isinstance(project_id, str), "project_id must be a string"

    events = [e for e in all_events if e.get("project_id") == project_id]
    if not events:
        return {}

    # --- idempotency guard -----------------------------------------------------
    run_id = _run_id_for(events)
    if metrics.run_already_ingested(project_id, run_id):
        return metrics.get_summary(project_id)

    transitions = [e for e in events if e["event"] == "STATE_TRANSITION"]

    # --- time-based metrics --------------------------------------------------
    metrics.record_event(project_id, "planning_time", _time_in_state(transitions, "PLANNING"), run_id=run_id)
    metrics.record_event(project_id, "implementation_time", _time_in_state(transitions, "BUILDING"), run_id=run_id)
    metrics.record_event(project_id, "testing_time", _time_in_state(transitions, "TESTING"), run_id=run_id)
    metrics.record_event(project_id, "debugging_time", _time_in_state(transitions, "DEBUGGING", "SECURITY_FIX"), run_id=run_id)

    # --- retries ---------------------------------------------------------------
    for e in events:
        if e["event"] == "RETRY":
            metrics.record_event(project_id, "retry", 1, run_id=run_id)

    # --- human approvals ---------------------------------------------------------
    # NOTE: the log does not currently distinguish an auto-approve from a real
    # human click (approval.py always emits HUMAN_APPROVAL with approved=true).
    # Flag this to the Leader — until it's fixed upstream, this count is not
    # reliable when --auto-approve is used.
    for e in events:
        if e["event"] == "HUMAN_APPROVAL" and e.get("approved"):
            metrics.record_event(project_id, "human_intervention", 1, run_id=run_id)

    # --- test pass/fail counts (parsed from the 'tests' GATE reason) -----------
    for e in events:
        if e["event"] == "GATE" and e.get("gate") == "tests":
            m = re.search(r"(\d+)/(\d+)", e.get("reason", ""))
            if m:
                passed, total = int(m.group(1)), int(m.group(2))
                metrics.record_event(project_id, "test_passed", passed, run_id=run_id)
                metrics.record_event(project_id, "test_failed", total - passed, run_id=run_id)

    # --- security findings (parsed from the security_agent AGENT_DONE summary) -
    for e in events:
        if e["event"] == "AGENT_DONE" and e.get("agent") == "security_agent":
            m = re.search(r"(\d+)\s+(CRITICAL|HIGH|MEDIUM|LOW)", e.get("summary", ""), re.I)
            if m:
                metrics.record_event(project_id, "security_finding", int(m.group(1)), run_id=run_id)

    # --- plan-stage decisions ----------------------------------------------------
    # Not stored here: per docs/agent_contracts.md, Decisions are produced by
    # the Plan/Architecture agent, which should call memory_agent.store()
    # directly once it returns real data (question/alternatives/decision/reason).
    # The current PlanStub only logs a free-text summary, no structured decision —
    # nothing reliable to extract yet. Revisit once Fati's real plan_agent lands.

    return metrics.get_summary(project_id)


if __name__ == "__main__":
    summary = ingest()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
