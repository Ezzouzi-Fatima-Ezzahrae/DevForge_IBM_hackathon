"""
orchestrator/contracts.py
Pydantic models for all shared DevForge data contracts.
Field names and allowed values match docs/agent_contracts.md exactly.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class ProjectStatus(str, Enum):
    IDLE               = "IDLE"
    PLANNING           = "PLANNING"
    BUILDING           = "BUILDING"
    TESTING            = "TESTING"
    DEBUGGING          = "DEBUGGING"
    SECURITY_FIX       = "SECURITY_FIX"
    SECURED            = "SECURED"
    AWAITING_APPROVAL  = "AWAITING_APPROVAL"
    RELEASED           = "RELEASED"
    FAILED             = "FAILED"   # retries exhausted or aborted; human escalation
    ERROR              = "ERROR"


class AgentStatus(str, Enum):
    PASS  = "PASS"
    FAIL  = "FAIL"
    ERROR = "ERROR"


class MilestoneStatus(str, Enum):
    PENDING   = "pending"
    BUILDING  = "building"
    TESTING   = "testing"
    APPROVED  = "approved"
    FAILED    = "failed"


class RequirementType(str, Enum):
    FUNCTIONAL     = "functional"
    NON_FUNCTIONAL = "non_functional"


class Priority(str, Enum):
    MUST_HAVE    = "must_have"
    SHOULD_HAVE  = "should_have"
    NICE_TO_HAVE = "nice_to_have"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class FindingType(str, Enum):
    BROKEN_ACCESS_CONTROL = "broken_access_control"
    INJECTION             = "injection"
    SECRETS_EXPOSURE      = "secrets_exposure"
    MISCONFIGURATION      = "misconfiguration"
    VULNERABLE_DEPENDENCY = "vulnerable_dependency"
    XSS                   = "xss"
    CSRF                  = "csrf"


class SecurityVerdict(str, Enum):
    PASS    = "PASS"
    BLOCKED = "BLOCKED"


class GateName(str, Enum):
    PLAN         = "plan"
    ARCHITECTURE = "architecture"
    TESTS        = "tests"
    SECURITY     = "security"
    RELEASE      = "release"


class GateVerdict(str, Enum):
    PASS    = "PASS"
    FAIL    = "FAIL"
    BLOCKED = "BLOCKED"


class MetricEventType(str, Enum):
    PLANNING_TIME        = "planning_time"
    IMPLEMENTATION_TIME  = "implementation_time"
    TESTING_TIME         = "testing_time"
    DEBUGGING_TIME       = "debugging_time"
    SECURITY_FINDING     = "security_finding"
    TEST_PASSED          = "test_passed"
    TEST_FAILED          = "test_failed"
    RETRY                = "retry"
    HUMAN_INTERVENTION   = "human_intervention"


# ─── Models ───────────────────────────────────────────────────────────────────

class Requirement(BaseModel):
    id: str                              # e.g. "REQ-001"
    type: RequirementType
    user_story: str
    acceptance_criteria: list[str] = Field(min_length=1)
    priority: Priority


class Milestone(BaseModel):
    id: str                              # e.g. "ms_001"
    title: str
    description: str
    order: int = Field(ge=1)
    requirement_ids: list[str] = Field(default_factory=list)
    status: MilestoneStatus = MilestoneStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)


class ProjectContext(BaseModel):
    project_id: str
    idea: str
    status: ProjectStatus = ProjectStatus.IDLE
    current_milestone_index: int = Field(default=0, ge=0)
    milestones: list[Milestone] = Field(default_factory=list)
    retries: dict[str, int] = Field(default_factory=lambda: {"plan": 0, "test": 0, "security": 0})
    human_approved_arch: bool = False
    human_approved_release: bool = False
    created_at: str                      # ISO 8601 UTC
    last_test_result: Optional[dict[str, Any]] = None


class AgentResult(BaseModel):
    agent: str
    status: AgentStatus
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float = Field(ge=0.0)
    timestamp: str                       # ISO 8601 UTC


class TestFailure(BaseModel):
    test: str
    error: str


class TestResultData(BaseModel):
    """Placed inside AgentResult.data by the Tester Agent.

    'status' mirrors the gate decision: PASS only when passed == total.
    Matches the shape documented in docs/tasks/manar.md.
    """
    __test__ = False  # prevent pytest from collecting this as a test class
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    status: AgentStatus                  # PASS only when passed == total
    failures: list[TestFailure] = Field(default_factory=list)
    coverage_percent: float = Field(ge=0.0, le=100.0)


class SecurityFinding(BaseModel):
    id: str                              # e.g. "SEC-001"
    severity: Severity
    type: FindingType
    location: str                        # "file/path.py:line"
    description: str
    recommended_fix: str


class Decision(BaseModel):
    id: str                              # e.g. "DEC-001"
    project_id: str
    question: str
    alternatives: list[str] = Field(min_length=1)
    decision: str
    reason: str
    source: str                          # agent name or "human"
    timestamp: str                       # ISO 8601 UTC


class GateResult(BaseModel):
    gate: GateName
    project_id: str
    milestone_id: Optional[str] = None  # null for plan/architecture/release
    verdict: GateVerdict
    reason: str
    retry_number: int = Field(default=0, ge=0)
    timestamp: str                       # ISO 8601 UTC


# ─── Validation helpers ───────────────────────────────────────────────────────

def validate_agent_result(data: dict) -> AgentResult:
    """Validate a raw dict against AgentResult. Raises ValidationError on failure."""
    return AgentResult.model_validate(data)


def validate_gate_result(data: dict) -> GateResult:
    """Validate a raw dict against GateResult. Raises ValidationError on failure."""
    return GateResult.model_validate(data)


def validate_security_finding(data: dict) -> SecurityFinding:
    """Validate a raw dict against SecurityFinding. Raises ValidationError on failure."""
    return SecurityFinding.model_validate(data)


def validate_decision(data: dict) -> Decision:
    """Validate a raw dict against Decision. Raises ValidationError on failure."""
    return Decision.model_validate(data)


def validate_requirement(data: dict) -> Requirement:
    """Validate a raw dict against Requirement. Raises ValidationError on failure."""
    return Requirement.model_validate(data)


def validate_milestone(data: dict) -> Milestone:
    """Validate a raw dict against Milestone. Raises ValidationError on failure."""
    return Milestone.model_validate(data)


def validate_project_context(data: dict) -> ProjectContext:
    """Validate a raw dict against ProjectContext. Raises ValidationError on failure."""
    return ProjectContext.model_validate(data)


def validate_test_result(data: dict) -> TestResultData:
    """Validate a raw dict against TestResultData. Raises ValidationError on failure."""
    return TestResultData.model_validate(data)
