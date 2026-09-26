from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from memory.schemas import EVENT_TYPES, MetricEvent

# ---------------------------------------------------------------------------
# Storage setup
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"
_METRICS_FILE = _DATA_DIR / "metrics.json"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()

# Maps event_type values to the summary dict key they increment / accumulate.
_SUMMARY_KEY_MAP: dict[str, str] = {
    "planning_time":        "planning_time_seconds",
    "implementation_time":  "implementation_time_seconds",
    "testing_time":         "testing_time_seconds",
    "debugging_time":       "debugging_time_seconds",
    "security_finding":     "security_findings_count",
    "test_passed":          "tests_passed",
    "test_failed":          "tests_failed",
    "retry":                "retry_count",
    "human_intervention":   "human_interventions",
}

_EMPTY_SUMMARY: dict[str, float] = {v: 0 for v in _SUMMARY_KEY_MAP.values()}

# Fail loudly at import time if _SUMMARY_KEY_MAP drifts out of sync with EVENT_TYPES.
assert _SUMMARY_KEY_MAP.keys() == EVENT_TYPES, (
    f"_SUMMARY_KEY_MAP keys do not match EVENT_TYPES.\n"
    f"  In _SUMMARY_KEY_MAP but not EVENT_TYPES: {_SUMMARY_KEY_MAP.keys() - EVENT_TYPES}\n"
    f"  In EVENT_TYPES but not _SUMMARY_KEY_MAP: {EVENT_TYPES - _SUMMARY_KEY_MAP.keys()}"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_all() -> list[dict]:
    if not _METRICS_FILE.exists():
        return []
    with _METRICS_FILE.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


def _save_all(events: list[dict]) -> None:
    with _METRICS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(events, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_event(
    project_id: str,
    event_type: str,
    value: float | int,
    *,
    run_id: str | None = None,
) -> None:
    """Append a metric event to metrics.json.

    *event_type* must be one of the recognised event types defined in
    :data:`memory.schemas.EVENT_TYPES`.

    If *run_id* is given, the event is tagged with it.  Callers that supply
    a *run_id* should first call :func:`run_already_ingested` to avoid
    double-counting a log run.

    Raises:
        ValueError: if *event_type* is not in ``EVENT_TYPES``.
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(
            f"Unknown event_type {event_type!r}. Must be one of: {sorted(EVENT_TYPES)}"
        )
    event = MetricEvent(
        project_id=project_id,
        event_type=event_type,
        value=float(value),
        timestamp=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
    )
    with _lock:
        events = _load_all()
        events.append(event.model_dump())
        _save_all(events)


def run_already_ingested(project_id: str, run_id: str) -> bool:
    """Return True if any metric event for *project_id* carries *run_id*.

    Used by :func:`memory.log_ingest.ingest` to make ingestion idempotent:
    calling ingest twice on the same log run will record the metrics only once.
    """
    return any(
        e.get("project_id") == project_id and e.get("run_id") == run_id
        for e in _load_all()
    )


def get_summary(project_id: str) -> dict:
    """Aggregate all metric events for *project_id* into a summary dict."""
    summary: dict[str, float] = dict(_EMPTY_SUMMARY)

    for event in _load_all():
        if event.get("project_id") != project_id:
            continue
        key = _SUMMARY_KEY_MAP.get(event.get("event_type", ""))
        if key is None:
            continue
        summary[key] += event.get("value", 0)

    # Return integer counts where the value is whole, keep floats for times
    return {
        k: int(v) if v == int(v) and not k.endswith("_seconds") else v
        for k, v in summary.items()
    }


def get_impact_summary(project_id: str) -> str:
    """Return a formatted human-readable summary for the demo."""
    s = get_summary(project_id)

    total_time = (
        s["planning_time_seconds"]
        + s["implementation_time_seconds"]
        + s["testing_time_seconds"]
        + s["debugging_time_seconds"]
    )

    lines = [
        f"📊 Impact Summary — project: {project_id}",
        "─" * 46,
        f"  ⏱  Total tracked time : {total_time:.3f}s",
        f"     • Planning         : {s['planning_time_seconds']:.3f}s",
        f"     • Implementation   : {s['implementation_time_seconds']:.3f}s",
        f"     • Testing          : {s['testing_time_seconds']:.3f}s",
        f"     • Debugging        : {s['debugging_time_seconds']:.3f}s",
        f"  ✅ Tests passed       : {s['tests_passed']}",
        f"  ❌ Tests failed       : {s['tests_failed']}",
        f"  🔐 Security findings  : {s['security_findings_count']}",
        f"  🔁 Retries            : {s['retry_count']}",
        f"  🙋 Human interventions: {s['human_interventions']}",
    ]
    return "\n".join(lines)
