"""
Demo / smoke-test for the Decision Memory and Metrics modules.

Run from the project root:
    python -m memory.demo_test
"""

from __future__ import annotations

import json
from pathlib import Path

# Clean slate: remove existing data files so each run is reproducible.
for _fname in ("decisions.json", "metrics.json", "gate_results.json"):
    _p = Path(__file__).parent / "data" / _fname
    if _p.exists():
        _p.unlink()

# ---------------------------------------------------------------------------
# Import public APIs
# ---------------------------------------------------------------------------
from memory.memory_agent import store, query, get_context, store_gate_result, query_gate_results
from memory.metrics import record_event, get_summary, get_impact_summary

PROJECT = "proj-devforge-001"

# ---------------------------------------------------------------------------
# 1. Store two decisions
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 1 — Storing decisions")
print("=" * 60)

id1 = store({
    "project_id": PROJECT,
    "question": "Which database should we use for persistent storage?",
    "alternatives": ["PostgreSQL", "SQLite", "MongoDB"],
    "decision": "PostgreSQL",
    "reason": "Production-grade, ACID-compliant, native JSON support.",
    "source": "architecture_agent",
})
print(f"  Stored: {id1}")

id2 = store({
    "project_id": PROJECT,
    "question": "Should we add Redis for caching?",
    "alternatives": ["Redis", "Memcached", "No cache"],
    "decision": "No cache",
    "reason": "Premature optimisation; revisit after performance profiling.",
    "source": "architecture_agent",
})
print(f"  Stored: {id2}")

# ---------------------------------------------------------------------------
# 2. Query decisions back
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 2 — Querying decisions")
print("=" * 60)

all_decisions = query(PROJECT)
print(f"  All decisions for {PROJECT}: {len(all_decisions)} found")

db_decisions = query(PROJECT, topic="database")
print(f"  Filtered by topic='database': {len(db_decisions)} found")
for d in db_decisions:
    print(f"    [{d['id']}] {d['question']}")

# ---------------------------------------------------------------------------
# 3. Record metric events
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 3 — Recording metric events")
print("=" * 60)

record_event(PROJECT, "planning_time", 42.5)
print("  Recorded: planning_time = 42.5s")

record_event(PROJECT, "test_passed", 1)
print("  Recorded: test_passed = 1")

record_event(PROJECT, "security_finding", 2)
print("  Recorded: security_finding = 2")

# ---------------------------------------------------------------------------
# 4. Print get_summary()
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 4 — get_summary()")
print("=" * 60)
summary = get_summary(PROJECT)
print(json.dumps(summary, indent=2))

# ---------------------------------------------------------------------------
# 5. Print get_context()
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 5 — get_context()")
print("=" * 60)
print(get_context(PROJECT))

# ---------------------------------------------------------------------------
# 6. Print get_impact_summary()
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 6 — get_impact_summary()")
print("=" * 60)
print(get_impact_summary(PROJECT))

# ---------------------------------------------------------------------------
# 7. Store gate results and query them back
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 7 — Gate results")
print("=" * 60)

store_gate_result({
    "gate": "tests",
    "project_id": PROJECT,
    "milestone_id": "m1",
    "verdict": "PASS",
    "reason": "All 42 unit tests passed with 94% coverage.",
    "retry_number": 0,
})
print("  Stored: tests / PASS")

store_gate_result({
    "gate": "security",
    "project_id": PROJECT,
    "verdict": "BLOCKED",
    "reason": "CVE-2024-1234 detected in dependency; patch required before release.",
    "retry_number": 1,
})
print("  Stored: security / BLOCKED")

gate_results = query_gate_results(PROJECT)
print(f"\n  All gate results for {PROJECT}: {len(gate_results)} found")
for r in gate_results:
    print(f"    [{r['gate'].upper()}] {r['verdict']} — {r['reason']}")

filtered = query_gate_results(PROJECT, gate="security")
print(f"\n  Filtered by gate='security': {len(filtered)} found")
for r in filtered:
    print(f"    [{r['gate'].upper()}] {r['verdict']} — {r['reason']}")
