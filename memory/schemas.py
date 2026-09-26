from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class Decision(BaseModel):
    id: str = Field(..., description="Decision identifier, e.g. DEC-0001")
    project_id: str
    question: str
    alternatives: List[str] = Field(min_length=1)
    decision: str
    reason: str
    source: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class GateResult(BaseModel):
    gate: Literal["plan", "architecture", "tests", "security", "release"]
    project_id: str
    milestone_id: Optional[str] = None
    verdict: Literal["PASS", "FAIL", "BLOCKED"]
    reason: str
    retry_number: int = Field(default=0, ge=0)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


EVENT_TYPES = {
    "planning_time",
    "implementation_time",
    "testing_time",
    "debugging_time",
    "security_finding",
    "test_passed",
    "test_failed",
    "retry",
    "human_intervention",
}


class MetricEvent(BaseModel):
    project_id: str
    event_type: str = Field(..., description=f"One of: {', '.join(sorted(EVENT_TYPES))}")
    value: float
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    run_id: Optional[str] = None  # set by log_ingest to prevent double-counting