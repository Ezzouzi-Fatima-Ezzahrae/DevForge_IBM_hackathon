"""
security/schemas.py
Models used only inside the security package (scanner, gate, agent).
Kept separate from memory/schemas.py and orchestrator/contracts.py; the
orchestrator adapter converts these to the shared contracts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class GateResult(BaseModel):
    gate: str                               # "plan" | "test" | "security"
    verdict: Literal["PASS", "BLOCKED", "FAIL", "ERROR"]
    milestone_id: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
