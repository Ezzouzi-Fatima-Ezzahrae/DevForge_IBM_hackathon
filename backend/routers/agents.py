"""
backend/routers/agents.py
GET /agents/results — returns all AgentResult records for a project.
GET /security      — returns SecurityFinding records for a milestone.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(tags=["agents"])

# ---------------------------------------------------------------------------
# In-memory store (replaced by real DB in production)
# ---------------------------------------------------------------------------

# Key: project_id → list of AgentResult dicts
_AGENT_RESULTS: Dict[str, List[Dict[str, Any]]] = {}

# Key: milestone_id → list of SecurityFinding dicts
_SECURITY_FINDINGS: Dict[str, List[Dict[str, Any]]] = {}


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class AgentResultResponse(BaseModel):
    agent: str
    milestone_id: str
    status: str
    summary: str
    duration_seconds: float = 0.0
    timestamp: Optional[str] = None


class SecurityFindingResponse(BaseModel):
    id: str
    severity: str
    category: str
    description: str
    file: str
    line: int
    cwe: str
    status: str
    evidence: Optional[str] = None
    recommendation: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/agents/results", response_model=List[AgentResultResponse])
def get_agent_results(project_id: str = Query(..., description="Project ID")):
    """Return all AgentResult records for a given project."""
    results = _AGENT_RESULTS.get(project_id, [])
    return results


@router.get("/security", response_model=List[SecurityFindingResponse])
def get_security_findings(
    milestone_id: str = Query(..., description="Milestone ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="Filter by status: OPEN, FIXED"),
):
    """
    Return SecurityFinding records for a given milestone.

    Optionally filter by severity or status.

    Example:
        GET /security?milestone_id=ms_001
        GET /security?milestone_id=ms_001&severity=HIGH
        GET /security?milestone_id=ms_001&status=OPEN
    """
    findings = _SECURITY_FINDINGS.get(milestone_id, [])

    if severity:
        severity_upper = severity.upper()
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        if severity_upper not in valid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid severity '{severity}'. Must be one of: {', '.join(sorted(valid))}",
            )
        findings = [f for f in findings if f.get("severity", "").upper() == severity_upper]

    if status:
        status_upper = status.upper()
        if status_upper not in ("OPEN", "FIXED"):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{status}'. Must be OPEN or FIXED.",
            )
        findings = [f for f in findings if f.get("status", "").upper() == status_upper]

    return findings


# ---------------------------------------------------------------------------
# Write helpers (called by the orchestrator / pipeline integration)
# ---------------------------------------------------------------------------

def store_agent_result(project_id: str, result: Dict[str, Any]) -> None:
    """Persist an AgentResult to the in-memory store."""
    _AGENT_RESULTS.setdefault(project_id, []).append(result)


def store_security_findings(milestone_id: str, findings: List[Dict[str, Any]]) -> None:
    """Persist SecurityFinding records for a milestone."""
    _SECURITY_FINDINGS.setdefault(milestone_id, [])
    # Upsert: update existing finding by id, or append new one
    existing = {f["id"]: f for f in _SECURITY_FINDINGS[milestone_id]}
    for finding in findings:
        existing[finding["id"]] = finding
    _SECURITY_FINDINGS[milestone_id] = list(existing.values())
