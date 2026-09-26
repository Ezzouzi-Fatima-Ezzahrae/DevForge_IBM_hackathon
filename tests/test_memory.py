"""
tests/test_memory.py

Pytest coverage for memory/memory_agent.py.
Metrics-specific tests live in tests/test_metrics.py.

Each test uses a unique project_id so tests never interfere with each
other or with real demo data on disk.
"""

from __future__ import annotations

import uuid

import pytest

from memory import memory_agent


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
# Task 8: get_context — top-5 cap and cross-project isolation
# --------------------------------------------------------------------------

def _make_decision(project_id: str, n: int) -> dict:
    """Helper: build a minimal valid decision dict for project_id."""
    return {
        "project_id": project_id,
        "question": f"Question {n}",
        "alternatives": [f"Option {n}A", f"Option {n}B"],
        "decision": f"Decision {n}",
        "reason": f"Reason {n}",
        "source": "plan_agent",
    }


def test_get_context_contains_expected_fields(project_id: str) -> None:
    """get_context must include id, question, decision, and reason for each entry."""
    memory_agent.store(_make_decision(project_id, 1))

    context = memory_agent.get_context(project_id)

    assert "DEC-" in context          # id
    assert "Question 1" in context    # question
    assert "Decision 1" in context    # decision
    assert "Reason 1" in context      # reason


def test_get_context_excludes_other_project(project_id: str) -> None:
    """Decisions from another project must never appear in get_context output."""
    other_id = f"other_{uuid.uuid4().hex[:8]}"

    memory_agent.store(_make_decision(project_id, 1))
    memory_agent.store(_make_decision(other_id, 99))

    context = memory_agent.get_context(project_id)

    assert "Question 1" in context
    assert "Question 99" not in context
    assert "Decision 99" not in context


def test_get_context_returns_at_most_5_decisions(project_id: str) -> None:
    """get_context must return no more than 5 decisions even when more are stored."""
    for i in range(1, 9):   # store 8 decisions
        memory_agent.store(_make_decision(project_id, i))

    context = memory_agent.get_context(project_id)
    lines = [l for l in context.splitlines() if l.strip()]

    assert len(lines) <= 5


def test_get_context_returns_most_recent_when_capped(project_id: str) -> None:
    """When more than 5 decisions exist, the last-stored ones must appear."""
    for i in range(1, 9):   # store 8 decisions; last stored are 4..8
        memory_agent.store(_make_decision(project_id, i))

    context = memory_agent.get_context(project_id)

    # Decisions 4-8 (the last 5 stored) must be present
    for i in range(4, 9):
        assert f"Question {i}" in context

    # Decisions 1-3 (the first 3 stored, outside the cap) must NOT appear
    for i in range(1, 4):
        assert f"Question {i}" not in context


def test_get_context_empty_returns_no_decisions_message(project_id: str) -> None:
    """An empty project must return the expected no-decisions message."""
    context = memory_agent.get_context(project_id)

    assert "No decisions recorded" in context
    assert project_id in context
