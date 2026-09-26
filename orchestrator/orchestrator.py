"""
orchestrator/orchestrator.py
Public entry point of the orchestrator.

The implementation lives in:
  state_machine.py  allowed states and transitions
  runner.py         pipeline loop, retries, parallel test + security
  gates.py          PASS / FAIL rules for every quality gate
"""

from orchestrator.runner import run_pipeline
from orchestrator.state_machine import StateMachine, InvalidTransitionError, TRANSITIONS

__all__ = ["run_pipeline", "StateMachine", "InvalidTransitionError", "TRANSITIONS"]
