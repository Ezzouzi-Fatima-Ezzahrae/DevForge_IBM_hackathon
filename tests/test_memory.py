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
