"""
tests/test_memory.py

Basic pytest coverage for memory/memory_agent.py and memory/metrics.py.
Each test uses a unique project_id so tests don't interfere with each
other or with real demo data on disk.
"""

from __future__ import annotations

import uuid

import pytest

from memory import memory_agent, metrics


@pytest.fixture
def project_id() -> str:
    return f"test_{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------
# memory_agent.py
# --------------------------------------------------------------------------


def test_store_and_query_decision(project_id: str) -> None:
    decision = {
        "project_id": project_id,
        "question": "Which database should we use?",
        "alternatives": ["PostgreSQL", "MongoDB", "SQLite"],
        "decision": "PostgreSQL",
        "reason": "Relational data with ACID transactions required",
        "source": "plan_agent",
    }

    decision_id = memory_agent.store(decision)
    assert decision_id.startswith("DEC-")

    results = memory_agent.query(project_id)
    assert len(results) == 1
    assert results[0]["decision"] == "PostgreSQL"
    assert results[0]["id"] == decision_id


def test_query_filters_by_topic(project_id: str) -> None:
    memory_agent.store({
        "project_id": project_id,
        "question": "Which database should we use?",
        "alternatives": ["PostgreSQL", "MongoDB"],
        "decision": "PostgreSQL",
        "reason": "ACID transactions required",
        "source": "plan_agent",
    })
    memory_agent.store({
        "project_id": project_id,
        "question": "Which frontend framework?",
        "alternatives": ["React", "Vue"],
        "decision": "React",
        "reason": "Team familiarity",
        "source": "plan_agent",
    })

    db_results = memory_agent.query(project_id, topic="database")
    assert len(db_results) == 1
    assert db_results[0]["decision"] == "PostgreSQL"

    all_results = memory_agent.query(project_id)
    assert len(all_results) == 2


def test_get_context_formats_decisions(project_id: str) -> None:
    memory_agent.store({
        "project_id": project_id,
        "question": "Which database should we use?",
        "alternatives": ["PostgreSQL", "MongoDB"],
        "decision": "PostgreSQL",
        "reason": "ACID transactions required",
        "source": "plan_agent",
    })

    context = memory_agent.get_context(project_id)
    assert "Which database should we use?" in context
    assert "PostgreSQL" in context
    assert "ACID transactions required" in context


def test_get_context_empty_project() -> None:
    empty_id = f"empty_{uuid.uuid4().hex[:8]}"
    context = memory_agent.get_context(empty_id)
    assert empty_id in context


# --------------------------------------------------------------------------
# metrics.py
# --------------------------------------------------------------------------


def test_record_event_and_get_summary(project_id: str) -> None:
    metrics.record_event(project_id, "planning_time", 12.5)
    metrics.record_event(project_id, "test_passed", 20)
    metrics.record_event(project_id, "test_failed", 3)
    metrics.record_event(project_id, "retry", 1)
    metrics.record_event(project_id, "retry", 1)
    metrics.record_event(project_id, "human_intervention", 1)

    summary = metrics.get_summary(project_id)

    assert summary["planning_time_seconds"] == 12.5
    assert summary["tests_passed"] == 20
    assert summary["tests_failed"] == 3
    assert summary["retry_count"] == 2
    assert summary["human_interventions"] == 1


def test_get_summary_only_counts_matching_project(project_id: str) -> None:
    other_id = f"other_{uuid.uuid4().hex[:8]}"

    metrics.record_event(project_id, "test_passed", 5)
    metrics.record_event(other_id, "test_passed", 999)

    summary = metrics.get_summary(project_id)
    assert summary["tests_passed"] == 5  # not polluted by other_id's events


def test_get_impact_summary_matches_get_summary(project_id: str) -> None:
    metrics.record_event(project_id, "test_passed", 10)
    metrics.record_event(project_id, "test_failed", 2)
    metrics.record_event(project_id, "security_finding", 1)

    summary = metrics.get_summary(project_id)
    impact_text = metrics.get_impact_summary(project_id)

    assert str(summary["tests_passed"]) in impact_text
    assert str(summary["tests_failed"]) in impact_text
    assert str(summary["security_findings_count"]) in impact_text


def test_get_summary_empty_project_returns_zeros() -> None:
    empty_id = f"empty_{uuid.uuid4().hex[:8]}"
    summary = metrics.get_summary(empty_id)

    assert summary["planning_time_seconds"] == 0
    assert summary["tests_passed"] == 0
    assert summary["retry_count"] == 0
