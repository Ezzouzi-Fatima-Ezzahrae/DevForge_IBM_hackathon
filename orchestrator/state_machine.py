"""
orchestrator/state_machine.py
Explicit FSM for the DevForge pipeline.
Reuses ProjectStatus from contracts.py — no redefinition.
"""

from orchestrator.contracts import ProjectStatus

# ─── Valid transitions ────────────────────────────────────────────────────────
# Maps each state to the states it may legally move into.

TRANSITIONS: dict[ProjectStatus, list[ProjectStatus]] = {
    ProjectStatus.IDLE: [
        ProjectStatus.PLANNING,
    ],
    ProjectStatus.PLANNING: [
        ProjectStatus.BUILDING,   # plan gate PASS
        ProjectStatus.FAILED,     # plan gate FAIL after max retries
    ],
    ProjectStatus.BUILDING: [
        ProjectStatus.TESTING,    # build done  → parallel test+security
    ],
    ProjectStatus.TESTING: [
        ProjectStatus.DEBUGGING,  # test gate FAIL, retries remaining
        ProjectStatus.SECURITY_FIX,  # tests PASS but security gate BLOCKED (checks run in parallel)
        ProjectStatus.SECURED,    # test gate PASS AND security gate PASS
        ProjectStatus.FAILED,     # test gate FAIL, retries exhausted
    ],
    ProjectStatus.DEBUGGING: [
        ProjectStatus.TESTING,    # patch applied → re-run tests
        ProjectStatus.SECURITY_FIX,  # security also blocked in the same round
        ProjectStatus.FAILED,     # debug itself failed
    ],
    ProjectStatus.SECURED: [
        ProjectStatus.SECURITY_FIX,     # security BLOCKED
        ProjectStatus.AWAITING_APPROVAL, # all gates PASS
    ],
    ProjectStatus.SECURITY_FIX: [
        ProjectStatus.TESTING,    # fix applied -> re-run tests + security in parallel
        ProjectStatus.SECURED,    # rescan after fix
        ProjectStatus.FAILED,     # security retries exhausted
    ],
    ProjectStatus.AWAITING_APPROVAL: [
        ProjectStatus.RELEASED,   # human approved
        ProjectStatus.BUILDING,   # human rejected → back to last milestone
        ProjectStatus.FAILED,     # human explicitly aborted
    ],
    ProjectStatus.RELEASED: [],   # terminal
    ProjectStatus.FAILED: [],     # terminal
    ProjectStatus.ERROR: [],      # terminal
}


class InvalidTransitionError(Exception):
    """Raised when a requested state transition is not in TRANSITIONS."""


class StateMachine:
    """
    Thin wrapper around TRANSITIONS that validates every move and
    stores the current state. The orchestrator calls advance() after
    each agent run or gate evaluation.
    """

    def __init__(self, initial: ProjectStatus = ProjectStatus.IDLE) -> None:
        self.state = initial

    def can_advance(self, target: ProjectStatus) -> bool:
        return target in TRANSITIONS.get(self.state, [])

    def advance(self, target: ProjectStatus) -> ProjectStatus:
        """Move to *target* or raise InvalidTransitionError."""
        if not self.can_advance(target):
            raise InvalidTransitionError(
                f"Cannot transition from {self.state.value} to {target.value}. "
                f"Allowed: {[s.value for s in TRANSITIONS.get(self.state, [])]}"
            )
        self.state = target
        return self.state
