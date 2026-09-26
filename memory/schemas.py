"""
memory/schemas.py
Shared Pydantic models used across the orchestrator, security gate, and memory agent.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# GateResult
# Returned by every quality gate (plan, test, security).
# The orchestrator reads this to decide the next state transition.
# ---------------------------------------------------------------------------

class GateResult(BaseModel):
    gate: str                               # "plan" | "test" | "security"
    verdict: Literal["PASS", "BLOCKED", "FAIL", "ERROR"]
    milestone_id: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Decision
# Written by the Memory Agent when an architectural or process decision is made.
# ---------------------------------------------------------------------------

class Decision(BaseModel):
    id: str                                 # e.g. "DEC-007"
    question: str
    alternatives: List[str] = Field(default_factory=list)
    decision: str
    reason: str
    source: str                             # agent name that produced this decision
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# SecurityFinding
# Canonical model shared between security/gate.py, security/scanner.py,
# security/security_agent.py, and the backend API.
# ---------------------------------------------------------------------------

class SecurityFinding(BaseModel):
    id: str                                 # e.g. "SEC-001"
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    category: str                           # e.g. "broken_access_control"
    description: str
    file: str                               # relative path
    line: int
    cwe: str                                # e.g. "CWE-639"
    status: Literal["OPEN", "FIXED"]
    evidence: Optional[str] = None
    recommendation: Optional[str] = None


# ---------------------------------------------------------------------------
# AgentResult
# Canonical output of every agent. The orchestrator only reads this shape.
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    agent: str
    milestone_id: str
    status: str                             # "PASS" | "BLOCKED" | "FAIL" | "ERROR"
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
