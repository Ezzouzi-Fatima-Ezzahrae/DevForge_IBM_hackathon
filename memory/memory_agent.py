from __future__ import annotations

import json
import threading
from datetime import datetime
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
            decision["timestamp"] = datetime.utcnow().isoformat() + "Z"

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


def query_gate_results(project_id: str, gate: str = None) -> list[dict]:
    """Return gate results for *project_id*, optionally filtered by *gate* name."""
    results = [r for r in _load_gate_results() if r.get("project_id") == project_id]
    if gate:
        results = [r for r in results if r.get("gate") == gate]
    return results


def get_context(project_id: str) -> str:
    """Return a human-readable summary of all decisions for *project_id*.

    Format per line:
        [DEC-NNN] <question> → <decision> (reason: <reason>)
    """
    decisions = query(project_id)
    if not decisions:
        return f"No decisions recorded for project '{project_id}'."

    lines = [
        f"[{d['id']}] {d['question']} → {d['decision']} (reason: {d['reason']})"
        for d in decisions
    ]
    return "\n".join(lines)
