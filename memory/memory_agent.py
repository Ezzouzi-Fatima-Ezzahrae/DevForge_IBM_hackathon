"""
memory/memory_agent.py
======================

Public API (for Ali and other agents)
--------------------------------------

query(project_id, topic=None) -> list[dict]
    Return all decisions stored for *project_id*, optionally filtered by
    a case-insensitive substring *topic* matched against question and reason.

query_gate_results(project_id, gate=None) -> list[dict]
    Return all gate results stored for *project_id*, optionally filtered by
    *gate* name (one of: plan, architecture, tests, security, release).

store(decision) -> str
    Validate and persist a decision dict; returns the assigned DEC-NNNN id.

store_gate_result(gate_result) -> None
    Validate and persist a gate-result dict.

get_context(project_id) -> str
    Return the 5 most-recently stored decisions for *project_id* formatted
    as a prompt prefix.  Returns an empty-context message when no decisions
    exist.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from memory.schemas import Decision, GateResult

# ---------------------------------------------------------------------------
# Storage setup
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"
_DECISIONS_FILE = _DATA_DIR / "decisions.json"
_GATE_RESULTS_FILE = _DATA_DIR / "gate_results.json"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_counter_lock = threading.Lock()


def _next_id() -> str:
    """Generate the next DEC-NNNN id based on existing entries."""
    decisions = _load_all()
    return f"DEC-{len(decisions) + 1:04d}"


def _load_all() -> list[dict]:
    """Return every decision stored on disk, or an empty list."""
    if not _DECISIONS_FILE.exists():
        return []
    with _DECISIONS_FILE.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


def _save_all(decisions: list[dict]) -> None:
    with _DECISIONS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(decisions, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def store(decision: dict) -> str:
    """Append *decision* to decisions.json and return its id.

    If the dict does not carry an 'id', one is assigned automatically.
    The dict is validated against the Decision schema before saving.
    """
    with _counter_lock:
        decisions = _load_all()

        # Assign id when not provided
        if not decision.get("id"):
            decision = dict(decision)
            decision["id"] = f"DEC-{len(decisions) + 1:04d}"

        # Assign timestamp when not provided
        if not decision.get("timestamp"):
            decision["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Validate via Pydantic
        validated = Decision(**decision)
        decisions.append(validated.model_dump())
        _save_all(decisions)

        return validated.id


def query(project_id: str, topic: Optional[str] = None) -> list[dict]:
    """Return decisions for *project_id*, optionally filtered by *topic*.

    *topic* is matched as a case-insensitive substring against the
    ``question`` and ``reason`` fields.
    """
    results = [d for d in _load_all() if d.get("project_id") == project_id]

    if topic:
        needle = topic.lower()
        results = [
            d
            for d in results
            if needle in d.get("question", "").lower()
            or needle in d.get("reason", "").lower()
        ]

    return results


# ---------------------------------------------------------------------------
# Gate results API
# ---------------------------------------------------------------------------


def _load_gate_results() -> list[dict]:
    """Return every gate result stored on disk, or an empty list."""
    if not _GATE_RESULTS_FILE.exists():
        return []
    with _GATE_RESULTS_FILE.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


def _save_gate_results(results: list[dict]) -> None:
    with _GATE_RESULTS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)


_gate_lock = threading.Lock()


def store_gate_result(gate_result: dict) -> None:
    """Validate *gate_result* against GateResult schema and append to gate_results.json."""
    with _gate_lock:
        validated = GateResult(**gate_result)
        results = _load_gate_results()
        results.append(validated.model_dump())
        _save_gate_results(results)


def query_gate_results(project_id: str, gate: str | None = None) -> list[dict]:
    """Return gate results for *project_id*, optionally filtered by *gate* name."""
    results = [r for r in _load_gate_results() if r.get("project_id") == project_id]
    if gate:
        results = [r for r in results if r.get("gate") == gate]
    return results


_CONTEXT_LIMIT = 5


def get_context(project_id: str) -> str:
    """Return the most-recently stored decisions for *project_id* as a prompt prefix.

    Only decisions belonging to *project_id* are included.
    At most :data:`_CONTEXT_LIMIT` (5) decisions are returned; when more are
    stored the **last** (most recently appended) ones are preferred, because
    recent decisions are most relevant as context.

    Format per line:
        [DEC-NNN] <question> → <decision> (reason: <reason>)

    Returns a clear empty-context message when no decisions exist.
    """
    all_decisions = query(project_id)
    if not all_decisions:
        return f"No decisions recorded for project '{project_id}'."

    # Take the last _CONTEXT_LIMIT entries (insertion order = append order).
    decisions = all_decisions[-_CONTEXT_LIMIT:]

    lines = [
        f"[{d['id']}] {d['question']} → {d['decision']} (reason: {d['reason']})"
        for d in decisions
    ]
    return "\n".join(lines)
