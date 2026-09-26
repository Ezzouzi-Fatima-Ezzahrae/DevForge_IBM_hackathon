"""
security/gate.py
Security gate evaluator — DevForge pipeline.

Rule (from ARCHITECTURE.md §5):
    PASS   → 0 CRITICAL and 0 HIGH findings with status OPEN
    BLOCKED → any CRITICAL or HIGH finding with status OPEN

MEDIUM / LOW / INFO findings are logged and included in details
but do NOT affect the verdict.

This module is the single location for gate logic.
No other file should re-implement this rule.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from memory.schemas import GateResult, SecurityFinding

logger = logging.getLogger(__name__)


def evaluate_security_gate(
    findings: List[SecurityFinding],
    milestone_id: str,
) -> GateResult:
    """
    Evaluate a list of SecurityFinding objects and return a GateResult.

    Args:
        findings:     List of SecurityFinding instances produced by the scanner.
        milestone_id: Identifier of the milestone being scanned.

    Returns:
        GateResult with verdict "PASS" or "BLOCKED".
    """
    # Only count OPEN findings — FIXED findings from a previous scan run
    # must not keep blocking the milestone.
    open_findings = [f for f in findings if f.status == "OPEN"]

    critical_count = sum(1 for f in open_findings if f.severity == "CRITICAL")
    high_count     = sum(1 for f in open_findings if f.severity == "HIGH")
    medium_count   = sum(1 for f in open_findings if f.severity == "MEDIUM")
    low_count      = sum(1 for f in open_findings if f.severity == "LOW")
    info_count     = sum(1 for f in open_findings if f.severity == "INFO")

    if critical_count == 0 and high_count == 0:
        verdict = "PASS"
    else:
        verdict = "BLOCKED"

    details = {
        "critical": critical_count,
        "high": high_count,
        "medium": medium_count,
        "low": low_count,
        "info": info_count,
        "total_open": len(open_findings),
        "total_findings": len(findings),
    }

    logger.info(
        "Security gate evaluated | milestone=%s verdict=%s "
        "critical=%d high=%d medium=%d low=%d",
        milestone_id,
        verdict,
        critical_count,
        high_count,
        medium_count,
        low_count,
    )

    return GateResult(
        gate="security",
        verdict=verdict,
        milestone_id=milestone_id,
        details=details,
        timestamp=datetime.now(timezone.utc),
    )
