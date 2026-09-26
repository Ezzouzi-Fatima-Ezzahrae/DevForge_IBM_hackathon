"""
orchestrator/gates.py
Quality gate evaluation functions.
Thresholds come from config/orchestrator_config.json — nothing is hard-coded here.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.contracts import (
    AgentResult,
    GateName,
    GateResult,
    GateVerdict,
    ProjectContext,
)

# ─── Config ───────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "orchestrator_config.json"
    with open(config_path) as f:
        return json.load(f)


def _cfg() -> dict:
    return _load_config()


# ─── Gate functions ───────────────────────────────────────────────────────────

def evaluate_plan_gate(result: AgentResult, context: ProjectContext) -> GateResult:
    """
    PASS: agent status PASS and ≥5 user stories and architecture has at least 1 ADR.
    FAIL: otherwise.
    """
    now = datetime.now(timezone.utc).isoformat()
    if result.status.value != "PASS":
        return GateResult(
            gate=GateName.PLAN,
            project_id=context.project_id,
            verdict=GateVerdict.FAIL,
            reason=f"Plan agent returned {result.status.value}: {result.summary}",
            retry_number=context.retries.get("plan", 0),
            timestamp=now,
        )
    reqs = result.data.get("requirements", [])
    adrs = result.data.get("architecture", {}).get("adr", [])
    if len(reqs) < 5:
        return GateResult(
            gate=GateName.PLAN,
            project_id=context.project_id,
            verdict=GateVerdict.FAIL,
            reason=f"Only {len(reqs)} user stories (need ≥5)",
            retry_number=context.retries.get("plan", 0),
            timestamp=now,
        )
    if not adrs:
        return GateResult(
            gate=GateName.PLAN,
            project_id=context.project_id,
            verdict=GateVerdict.FAIL,
            reason="Architecture has no ADR entries",
            retry_number=context.retries.get("plan", 0),
            timestamp=now,
        )
    return GateResult(
        gate=GateName.PLAN,
        project_id=context.project_id,
        verdict=GateVerdict.PASS,
        reason=f"{len(reqs)} user stories, {len(adrs)} ADR(s)",
        retry_number=context.retries.get("plan", 0),
        timestamp=now,
    )


def evaluate_test_gate(
    result: AgentResult,
    context: ProjectContext,
    milestone_id: str | None = None,
) -> GateResult:
    """
    PASS: passed == total (100%).  Threshold from config.
    FAIL: anything less.
    """
    now = datetime.now(timezone.utc).isoformat()
    retry = context.retries.get("test", 0)

    if result.status.value == "ERROR":
        return GateResult(
            gate=GateName.TESTS,
            project_id=context.project_id,
            milestone_id=milestone_id,
            verdict=GateVerdict.FAIL,
            reason=f"Tester agent errored: {result.summary}",
            retry_number=retry,
            timestamp=now,
        )

    data = result.data
    total = data.get("total", 0)
    passed = data.get("passed", 0)

    # Config says "all_pass" → 100%
    pass_condition = _cfg()["gates"]["tests"]["pass_condition"]
    gate_pass = (passed == total) if pass_condition == "all_pass" else (passed >= total * 0.8)

    if gate_pass:
        return GateResult(
            gate=GateName.TESTS,
            project_id=context.project_id,
            milestone_id=milestone_id,
            verdict=GateVerdict.PASS,
            reason=f"{passed}/{total} tests passed, coverage {data.get('coverage_percent', 0):.0f}%",
            retry_number=retry,
            timestamp=now,
        )
    failures = data.get("failures", [])
    fail_names = ", ".join(f["test"] for f in failures[:3])
    return GateResult(
        gate=GateName.TESTS,
        project_id=context.project_id,
        milestone_id=milestone_id,
        verdict=GateVerdict.FAIL,
        reason=f"{passed}/{total} passed. Failures: {fail_names}",
        retry_number=retry,
        timestamp=now,
    )


def evaluate_security_gate(
    result: AgentResult,
    context: ProjectContext,
    milestone_id: str | None = None,
) -> GateResult:
    """
    PASS: zero critical, zero high findings.
    BLOCKED: any critical or high finding.
    """
    now = datetime.now(timezone.utc).isoformat()
    retry = context.retries.get("security", 0)
    block_on = set(_cfg()["gates"]["security"]["block_on_severities"])

    if result.status.value == "ERROR":
        return GateResult(
            gate=GateName.SECURITY,
            project_id=context.project_id,
            milestone_id=milestone_id,
            verdict=GateVerdict.BLOCKED,
            reason=f"Security agent errored: {result.summary}",
            retry_number=retry,
            timestamp=now,
        )

    data = result.data
    verdict = data.get("verdict", "BLOCKED")
    counts = data.get("counts", {})
    findings = data.get("findings", [])

    blocking = [f for f in findings if f.get("severity") in block_on]
    if blocking or verdict == "BLOCKED":
        desc = "; ".join(
            f"{f['severity'].upper()} {f.get('type','?')} at {f.get('location','?')}"
            for f in blocking[:3]
        )
        return GateResult(
            gate=GateName.SECURITY,
            project_id=context.project_id,
            milestone_id=milestone_id,
            verdict=GateVerdict.BLOCKED,
            reason=f"{len(blocking)} blocking finding(s): {desc or result.summary}",
            retry_number=retry,
            timestamp=now,
        )

    return GateResult(
        gate=GateName.SECURITY,
        project_id=context.project_id,
        milestone_id=milestone_id,
        verdict=GateVerdict.PASS,
        reason=(
            f"No critical/high findings. "
            f"medium={counts.get('medium',0)} low={counts.get('low',0)}"
        ),
        retry_number=retry,
        timestamp=now,
    )


def evaluate_release_gate(context: ProjectContext) -> GateResult:
    """
    PASS: human_approved_release is True.
    FAIL: not yet approved.
    """
    now = datetime.now(timezone.utc).isoformat()
    if context.human_approved_release:
        return GateResult(
            gate=GateName.RELEASE,
            project_id=context.project_id,
            verdict=GateVerdict.PASS,
            reason="Human approved release",
            timestamp=now,
        )
    return GateResult(
        gate=GateName.RELEASE,
        project_id=context.project_id,
        verdict=GateVerdict.FAIL,
        reason="Awaiting human release approval",
        timestamp=now,
    )
