"""
orchestrator/approval_broker.py
Lets a human approve/reject from somewhere other than the terminal (the API).

How it works
------------
* The pipeline thread calls ``broker.request(...)`` (through the function that
  ``make_approval_fn`` builds).  It blocks until somebody resolves it or the
  timeout expires.
* The API thread calls ``broker.pending(project_id)`` to see what the human must
  look at, then ``broker.resolve(project_id, approved)`` when the button is clicked.
* Timeout, cancel or any error  ->  treated as REJECTION (never an accidental approval).

Thread-safe. No I/O, no dependencies outside the standard library and contracts.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from orchestrator.contracts import GateResult, ProjectContext

DEFAULT_TIMEOUT_SECONDS = 600.0


@dataclass
class _Request:
    project_id: str
    prompt: str
    idea: str
    gates: list[dict]
    created_at: float = field(default_factory=time.time)
    event: threading.Event = field(default_factory=threading.Event)
    approved: bool = False


class ApprovalBroker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, _Request] = {}

    # ── pipeline side ────────────────────────────────────────────────────────
    def request(
        self,
        context: ProjectContext,
        gate_results: list[GateResult],
        prompt_text: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> bool:
        """Block until resolved. Returns False on timeout/cancel."""
        req = _Request(
            project_id=context.project_id,
            prompt=prompt_text,
            idea=context.idea,
            gates=[_gate_to_dict(g) for g in gate_results],
        )
        with self._lock:
            self._requests[context.project_id] = req
        try:
            answered = req.event.wait(timeout)
            return bool(answered and req.approved)
        finally:
            with self._lock:
                if self._requests.get(context.project_id) is req:
                    del self._requests[context.project_id]

    # ── API side ─────────────────────────────────────────────────────────────
    def pending(self, project_id: str) -> dict | None:
        """What the human must see, or None if nothing is waiting."""
        with self._lock:
            req = self._requests.get(project_id)
        if req is None or req.event.is_set():
            return None
        return {
            "project_id": req.project_id,
            "prompt": req.prompt,
            "idea": req.idea,
            "gates": req.gates,
            "waiting_seconds": round(time.time() - req.created_at, 1),
        }

    def resolve(self, project_id: str, approved: bool) -> bool:
        """Answer the pending request. Returns False if nothing was waiting."""
        with self._lock:
            req = self._requests.get(project_id)
        if req is None or req.event.is_set():
            return False
        req.approved = bool(approved)
        req.event.set()
        return True

    def cancel(self, project_id: str) -> bool:
        """Reject a waiting request (used by reset)."""
        return self.resolve(project_id, False)


def _gate_to_dict(g: GateResult) -> dict:
    return {
        "gate": g.gate.value,
        "verdict": g.verdict.value,
        "reason": g.reason,
    }


# One shared broker for the whole process (API + pipeline threads).
broker = ApprovalBroker()


def make_approval_fn(
    project_id: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    target: ApprovalBroker | None = None,
) -> Callable[..., bool]:
    """
    Build a function with the same signature as ``request_approval_cli`` so it
    can be passed to ``run_pipeline(approval_fn=...)``.
    """
    b = target or broker

    def approval_fn(
        context: ProjectContext,
        gate_results: list[GateResult],
        prompt_text: str = "Approve and continue?",
        auto_approve: bool = False,
    ) -> bool:
        if auto_approve:
            return True
        try:
            return b.request(context, gate_results, prompt_text, timeout)
        except Exception:  # never approve by accident
            return False

    return approval_fn
