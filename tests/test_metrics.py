"""
tests/test_metrics.py

Pytest coverage for memory/metrics.py and the log_ingest idempotency guarantee.

Each test uses a unique project_id (uuid-based) so tests never interfere with
each other or with any real demo data on disk.

The log_ingest tests use tmp_path and monkeypatch to redirect both the log
source (LOG_FILE) and the metrics store (_METRICS_FILE) to isolated temp files,
so they never touch the repository's real logs/orchestrator.jsonl.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from memory import metrics as metrics_mod
from memory.log_ingest import ingest, _run_id_for


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pid() -> str:
    """Return a fresh unique project_id."""
    return f"test_{uuid.uuid4().hex[:8]}"


def _make_log(project_id: str, tmp_path: Path) -> Path:
    """Write a minimal but realistic orchestrator.jsonl to *tmp_path* and
    return its Path.

    Contains:
      - IDLE → PLANNING → BUILDING (STATE_TRANSITION events with real timestamps)
      - 1 RETRY event
      - 1 HUMAN_APPROVAL event
      - 1 GATE (tests) event: 17/20 tests passed
      - 1 AGENT_DONE (security_agent) event: 1 HIGH finding
    """
    events = [
        {"project_id": project_id, "event": "STATE_TRANSITION", "from": "IDLE",     "to": "PLANNING", "ts": "2025-01-01T10:00:00"},
        {"project_id": project_id, "event": "STATE_TRANSITION", "from": "PLANNING", "to": "BUILDING", "ts": "2025-01-01T10:01:00"},
        {"project_id": project_id, "event": "RETRY",             "ts": "2025-01-01T10:02:00"},
        {"project_id": project_id, "event": "HUMAN_APPROVAL",    "approved": True,   "ts": "2025-01-01T10:03:00"},
        {"project_id": project_id, "event": "GATE",              "gate": "tests",    "reason": "17/20 tests passed", "ts": "2025-01-01T10:04:00"},
        {"project_id": project_id, "event": "AGENT_DONE",        "agent": "security_agent", "summary": "1 HIGH finding", "ts": "2025-01-01T10:05:00"},
    ]
    log_file = tmp_path / "orchestrator.jsonl"
    log_file.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return log_file


def _isolated_metrics_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect metrics storage to an isolated temp file for this test."""
    metrics_file = tmp_path / "metrics.json"
    monkeypatch.setattr(metrics_mod, "_METRICS_FILE", metrics_file)
    return metrics_file


# ---------------------------------------------------------------------------
# record_event / get_summary
# ---------------------------------------------------------------------------


def test_record_event_and_get_summary() -> None:
    pid = _pid()
    metrics_mod.record_event(pid, "planning_time", 12.5)
    metrics_mod.record_event(pid, "test_passed", 20)
    metrics_mod.record_event(pid, "test_failed", 3)
    metrics_mod.record_event(pid, "retry", 1)
    metrics_mod.record_event(pid, "retry", 1)
    metrics_mod.record_event(pid, "human_intervention", 1)

    s = metrics_mod.get_summary(pid)

    assert s["planning_time_seconds"] == 12.5
    assert s["tests_passed"] == 20
    assert s["tests_failed"] == 3
    assert s["retry_count"] == 2
    assert s["human_interventions"] == 1


def test_summary_contains_all_keys() -> None:
    """get_summary always returns every expected key, even for a project with no events."""
    pid = _pid()
    s = metrics_mod.get_summary(pid)

    expected_keys = {
        "planning_time_seconds",
        "implementation_time_seconds",
        "testing_time_seconds",
        "debugging_time_seconds",
        "security_findings_count",
        "tests_passed",
        "tests_failed",
        "retry_count",
        "human_interventions",
    }
    assert set(s.keys()) == expected_keys


def test_empty_project_returns_zeros() -> None:
    pid = _pid()
    s = metrics_mod.get_summary(pid)

    assert s["planning_time_seconds"] == 0
    assert s["tests_passed"] == 0
    assert s["retry_count"] == 0
    assert s["security_findings_count"] == 0


def test_project_isolation() -> None:
    """Events for one project must never affect another project's summary."""
    pid_a = _pid()
    pid_b = _pid()

    metrics_mod.record_event(pid_a, "test_passed", 5)
    metrics_mod.record_event(pid_b, "test_passed", 999)

    assert metrics_mod.get_summary(pid_a)["tests_passed"] == 5
    assert metrics_mod.get_summary(pid_b)["tests_passed"] == 999


def test_count_fields_are_integers() -> None:
    """Non-time summary fields must be ints (not floats) when values are whole numbers."""
    pid = _pid()
    metrics_mod.record_event(pid, "retry", 3)
    metrics_mod.record_event(pid, "test_passed", 10)

    s = metrics_mod.get_summary(pid)
    assert isinstance(s["retry_count"], int)
    assert isinstance(s["tests_passed"], int)


def test_time_fields_are_floats() -> None:
    """Time summary fields must stay as floats even when their value is whole."""
    pid = _pid()
    metrics_mod.record_event(pid, "planning_time", 60.0)

    s = metrics_mod.get_summary(pid)
    assert isinstance(s["planning_time_seconds"], float)


def test_unknown_event_type_raises() -> None:
    pid = _pid()
    with pytest.raises(ValueError, match="Unknown event_type"):
        metrics_mod.record_event(pid, "not_a_real_event", 1)


# ---------------------------------------------------------------------------
# get_impact_summary
# ---------------------------------------------------------------------------


def test_impact_summary_matches_get_summary() -> None:
    pid = _pid()
    metrics_mod.record_event(pid, "test_passed", 10)
    metrics_mod.record_event(pid, "test_failed", 2)
    metrics_mod.record_event(pid, "security_finding", 1)

    s = metrics_mod.get_summary(pid)
    text = metrics_mod.get_impact_summary(pid)

    assert str(s["tests_passed"]) in text
    assert str(s["tests_failed"]) in text
    assert str(s["security_findings_count"]) in text


def test_impact_summary_time_uses_3_decimal_places() -> None:
    pid = _pid()
    metrics_mod.record_event(pid, "planning_time", 0.003)

    text = metrics_mod.get_impact_summary(pid)
    # Must render "0.003s", NOT "0.0s"
    assert "0.003s" in text


def test_impact_summary_contains_project_id() -> None:
    pid = _pid()
    text = metrics_mod.get_impact_summary(pid)
    assert pid in text


# ---------------------------------------------------------------------------
# run_already_ingested
# ---------------------------------------------------------------------------


def test_run_already_ingested_false_when_no_events() -> None:
    pid = _pid()
    assert metrics_mod.run_already_ingested(pid, "some-run-id") is False


def test_run_already_ingested_true_after_record() -> None:
    pid = _pid()
    metrics_mod.record_event(pid, "retry", 1, run_id="run-abc")
    assert metrics_mod.run_already_ingested(pid, "run-abc") is True


def test_run_already_ingested_false_for_different_run_id() -> None:
    pid = _pid()
    metrics_mod.record_event(pid, "retry", 1, run_id="run-abc")
    assert metrics_mod.run_already_ingested(pid, "run-xyz") is False


# ---------------------------------------------------------------------------
# log_ingest idempotency — the regression test
# ---------------------------------------------------------------------------


def test_ingest_does_not_double_count_on_second_call(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Regression test: calling ingest() twice on the SAME log run must NOT
    double the metrics.

    This test:
    1. Writes a known log file to a temp location.
    2. Redirects LOG_FILE and _METRICS_FILE to isolated temp files.
    3. Calls ingest() once — records the first summary.
    4. Calls ingest() a SECOND time without touching the log.
    5. Asserts every metric value is IDENTICAL between call 1 and call 2.

    No manual metric reset is performed between the two calls.
    """
    import memory.log_ingest as log_ingest_mod

    pid = _pid()
    log_file = _make_log(pid, tmp_path)
    _isolated_metrics_file(tmp_path, monkeypatch)

    # Redirect ingest's LOG_FILE to our isolated temp log
    monkeypatch.setattr(log_ingest_mod, "LOG_FILE", log_file)

    # First ingest
    summary_first = ingest(pid)

    # Second ingest — same log, same project_id, no changes anywhere
    summary_second = ingest(pid)

    # Every counter and time value must be identical
    assert summary_first == summary_second, (
        f"Double ingest produced different summaries:\n"
        f"  first : {summary_first}\n"
        f"  second: {summary_second}"
    )


def test_ingest_correct_values_from_known_log(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Ingest a known log fixture and verify the resulting summary contains
    exactly the values we expect from that fixture.
    """
    import memory.log_ingest as log_ingest_mod

    pid = _pid()
    log_file = _make_log(pid, tmp_path)
    _isolated_metrics_file(tmp_path, monkeypatch)
    monkeypatch.setattr(log_ingest_mod, "LOG_FILE", log_file)

    summary = ingest(pid)

    # The fixture has 1 RETRY event
    assert summary["retry_count"] == 1
    # The fixture has 1 HUMAN_APPROVAL event
    assert summary["human_interventions"] == 1
    # The fixture GATE reason is "17/20 tests passed" → 17 passed, 3 failed
    assert summary["tests_passed"] == 17
    assert summary["tests_failed"] == 3
    # The fixture AGENT_DONE summary is "1 HIGH finding"
    assert summary["security_findings_count"] == 1


def test_ingest_empty_log_returns_empty_dict(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    import memory.log_ingest as log_ingest_mod

    empty_log = tmp_path / "orchestrator.jsonl"
    empty_log.write_text("", encoding="utf-8")
    monkeypatch.setattr(log_ingest_mod, "LOG_FILE", empty_log)

    assert ingest() == {}


def test_run_id_for_is_deterministic() -> None:
    """_run_id_for must produce the same hash for identical event lists."""
    events = [
        {"project_id": "proj-1", "event": "RETRY", "ts": "2025-01-01T10:00:00"},
        {"project_id": "proj-1", "event": "GATE",  "ts": "2025-01-01T10:01:00"},
    ]
    assert _run_id_for(events) == _run_id_for(events)
    assert _run_id_for(events) == _run_id_for(list(reversed(events)))  # order-independent
