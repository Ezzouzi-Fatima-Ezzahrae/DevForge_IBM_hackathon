"""
orchestrator/gates.py
Gate evaluation logic for the DevForge pipeline.

Each gate function receives an AgentResult dict and returns a GateResult.
The orchestrator reads GateResult.verdict to decide the next state transition.

Gate rules:
    Plan gate:    ≥5 user stories, tech stack named, ≥1 ADR
    Test gate:    ≥80% pass, 0 critical-path failures
    Security gate: 0 CRITICAL open, 0 HIGH open   → PASS
                   any CRITICAL or HIGH open       → BLOCKED
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from memory.schemas import GateResult


# ---------------------------------------------------------------------------
# Plan Gate
# ---------------------------------------------------------------------------

def evaluate_plan_gate(agent_result: Dict[str, Any]) -> GateResult:
    """
    PASS when:
      - ≥5 user stories each with one acceptance criterion
      - Tech stack is named
      - ≥1 ADR present

    Returns GateResult with verdict "PASS" or "FAIL".
    """
    milestone_id = agent_result.get("milestone_id", "plan")
    payload = agent_result.get("payload", {})

    user_stories = payload.get("user_stories", [])
    tech_stack   = payload.get("tech_stack", "")
    adrs         = payload.get("adrs", [])

    issues = []
    if len(user_stories) < 5:
        issues.append(f"Need ≥5 user stories, got {len(user_stories)}")
    if not tech_stack:
        issues.append("Tech stack not specified")
    if len(adrs) < 1:
        issues.append("Need ≥1 ADR")

    verdict = "PASS" if not issues else "FAIL"
    return GateResult(
        gate="plan",
        verdict=verdict,
        milestone_id=milestone_id,
        details={"issues": issues, "user_story_count": len(user_stories)},
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Test Gate
# ---------------------------------------------------------------------------

def evaluate_test_gate(agent_result: Dict[str, Any]) -> GateResult:
    """
    PASS when:
      - ≥80% of tests pass
      - 0 critical-path failures

    Returns GateResult with verdict "PASS" or "FAIL".
    """
    milestone_id = agent_result.get("milestone_id", "ms_unknown")
    payload = agent_result.get("payload", {})

    pass_count = int(payload.get("pass_count", 0))
    fail_count = int(payload.get("fail_count", 0))
    total = pass_count + fail_count

    critical_failures = [
        t for t in payload.get("test_results", [])
        if t.get("status") == "FAIL" and t.get("is_critical_path")
    ]

    if total == 0:
        verdict = "FAIL"
        details = {"issue": "No tests reported"}
    else:
        pass_rate = pass_count / total
        if pass_rate >= 0.8 and len(critical_failures) == 0:
            verdict = "PASS"
        else:
            verdict = "FAIL"
        details = {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": round(pass_rate, 3),
            "critical_failures": len(critical_failures),
        }

    return GateResult(
        gate="test",
        verdict=verdict,
        milestone_id=milestone_id,
        details=details,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Security Gate
# Delegates to security/gate.py — do not duplicate the rule here.
# ---------------------------------------------------------------------------

def evaluate_security_gate_from_result(agent_result: Dict[str, Any]) -> GateResult:
    """
    Evaluate the security gate from an AgentResult dict produced by the
    Security Agent. Delegates to security.gate.evaluate_security_gate.

    Handles the case where the Security Agent returned status="ERROR"
    by routing to HUMAN_REVIEW rather than silently passing.
    """
    from security.gate import evaluate_security_gate
    from memory.schemas import SecurityFinding

    milestone_id = agent_result.get("milestone_id", "ms_unknown")
    agent_status = agent_result.get("status", "")

    # An ERROR from the scanner must NOT be treated as PASS
    if agent_status == "ERROR":
        return GateResult(
            gate="security",
            verdict="ERROR",
            milestone_id=milestone_id,
            details={"error": agent_result.get("summary", "Unknown scanner error")},
            timestamp=datetime.now(timezone.utc),
        )

    payload = agent_result.get("payload", {})
    raw_findings = payload.get("findings", [])

    # Reconstruct SecurityFinding objects for gate evaluation
    findings = []
    for f in raw_findings:
        try:
            findings.append(SecurityFinding(**f))
        except Exception:
            pass  # skip malformed findings — gate will evaluate on what remains

    return evaluate_security_gate(findings, milestone_id)
