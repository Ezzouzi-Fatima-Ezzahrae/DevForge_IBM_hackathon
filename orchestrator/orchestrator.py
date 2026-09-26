"""
orchestrator/orchestrator.py
Main FSM — DevForge pipeline.

State transitions (from ARCHITECTURE.md §4):

    IDLE              + create(idea)                → PLANNING
    PLANNING          + plan_gate PASS              → BUILDING
    PLANNING          + plan_gate FAIL, retry<2     → PLANNING
    PLANNING          + plan_gate FAIL, retry=2     → HUMAN_REVIEW

    BUILDING          + build done                  → TESTING

    TESTING           + both PASS                   → MILESTONE_APPROVED
    TESTING           + test FAIL, retry<3          → DEBUGGING
    TESTING           + test FAIL, retry=3          → HUMAN_REVIEW
    TESTING           + sec BLOCKED, retry<2        → SECURITY_FIX
    TESTING           + sec BLOCKED, retry=2        → HUMAN_REVIEW

    DEBUGGING         + patch applied               → TESTING
    SECURITY_FIX      + patch applied               → TESTING  (re-run both)

    MILESTONE_APPROVED + more milestones            → BUILDING
    MILESTONE_APPROVED + all done                   → AWAITING_APPROVAL

    AWAITING_APPROVAL + human approves              → RELEASED
    AWAITING_APPROVAL + human rejects               → BUILDING

Single state owner: only this class writes project.status.
Agents are stateless workers; they return results, not decisions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from orchestrator.gates import evaluate_plan_gate
from orchestrator.runner import merge, run_parallel_sync

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State enum
# ---------------------------------------------------------------------------

class ProjectStatus(str, Enum):
    IDLE               = "IDLE"
    PLANNING           = "PLANNING"
    BUILDING           = "BUILDING"
    TESTING            = "TESTING"
    DEBUGGING          = "DEBUGGING"
    SECURITY_FIX       = "SECURITY_FIX"
    MILESTONE_APPROVED = "MILESTONE_APPROVED"
    AWAITING_APPROVAL  = "AWAITING_APPROVAL"
    RELEASED           = "RELEASED"
    HUMAN_REVIEW       = "HUMAN_REVIEW"
    ERROR              = "ERROR"


# ---------------------------------------------------------------------------
# Max retry limits
# ---------------------------------------------------------------------------

MAX_PLAN_RETRIES     = 2
MAX_TEST_RETRIES     = 3   # debug cycles
MAX_SECURITY_RETRIES = 2   # security-fix cycles


# ---------------------------------------------------------------------------
# Project context (in-memory, mirrored to DB by the backend)
# ---------------------------------------------------------------------------

@dataclass
class ProjectContext:
    project_id: str
    idea: str
    status: str = ProjectStatus.IDLE
    current_milestone_index: int = 0
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    retries: Dict[str, int] = field(
        default_factory=lambda: {"plan": 0, "test": 0, "security": 0}
    )
    human_approved_arch: bool = False
    human_approved_release: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_results: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Orchestrator FSM
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    DevForge pipeline FSM.

    Usage:
        orch = Orchestrator(
            plan_fn=plan_agent.run,
            builder_fn=builder_agent.run,
            tester_fn=tester_agent.run,
            security_fn=security_agent.run,
            debugger_fn=debugger_agent.run,
        )
        ctx = orch.create_project("proj_001", "A task-management SaaS")
        orch.run(ctx)
    """

    def __init__(
        self,
        plan_fn: Callable[[Dict], Dict],
        builder_fn: Callable[[Dict], Dict],
        tester_fn: Callable[[Dict], Dict],
        security_fn: Callable[[Dict], Dict],
        debugger_fn: Callable[[Dict], Dict],
        on_status_change: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.plan_fn     = plan_fn
        self.builder_fn  = builder_fn
        self.tester_fn   = tester_fn
        self.security_fn = security_fn
        self.debugger_fn = debugger_fn
        # Optional callback: on_status_change(project_id, new_status)
        self.on_status_change = on_status_change

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_project(self, project_id: str, idea: str) -> ProjectContext:
        ctx = ProjectContext(project_id=project_id, idea=idea)
        self._set_status(ctx, ProjectStatus.IDLE)
        return ctx

    def run(self, ctx: ProjectContext) -> ProjectContext:
        """
        Drive the project through the pipeline from IDLE to RELEASED.
        Returns the final ProjectContext.
        """
        self._set_status(ctx, ProjectStatus.PLANNING)

        # ---------------------------------------------------------------
        # PLAN phase
        # ---------------------------------------------------------------
        plan_result = self._invoke_agent("plan_agent", self.plan_fn, {"idea": ctx.idea})
        ctx.agent_results.append(plan_result)

        plan_gate = evaluate_plan_gate(plan_result)

        while plan_gate.verdict != "PASS":
            ctx.retries["plan"] += 1
            if ctx.retries["plan"] >= MAX_PLAN_RETRIES:
                return self._escalate(ctx, "Plan gate failed after max retries")
            logger.info("Plan gate FAIL — retry %d/%d", ctx.retries["plan"], MAX_PLAN_RETRIES)
            plan_result = self._invoke_agent(
                "plan_agent",
                self.plan_fn,
                {"idea": ctx.idea, "feedback": plan_gate.details},
            )
            ctx.agent_results.append(plan_result)
            plan_gate = evaluate_plan_gate(plan_result)

        # ---------------------------------------------------------------
        # HUMAN APPROVAL — architecture
        # ---------------------------------------------------------------
        self._set_status(ctx, "AWAITING_ARCH_APPROVAL")
        logger.info("Waiting for human architecture approval | project=%s", ctx.project_id)
        # In the real system the backend waits for POST /projects/{id}/approve
        # For the synchronous test runner we assume approval is granted
        ctx.human_approved_arch = True

        # ---------------------------------------------------------------
        # MILESTONE loop
        # ---------------------------------------------------------------
        milestones = plan_result.get("payload", {}).get("milestones", ["ms_001"])
        ctx.milestones = milestones

        for idx, milestone in enumerate(milestones):
            ctx.current_milestone_index = idx
            milestone_id = milestone if isinstance(milestone, str) else milestone.get("id", f"ms_{idx:03d}")
            ctx = self._run_milestone(ctx, milestone_id)

            if ctx.status in (ProjectStatus.HUMAN_REVIEW, ProjectStatus.ERROR):
                return ctx

        # ---------------------------------------------------------------
        # AWAITING RELEASE APPROVAL
        # ---------------------------------------------------------------
        self._set_status(ctx, ProjectStatus.AWAITING_APPROVAL)
        logger.info("All milestones approved. Awaiting release approval.")
        return ctx

    # ------------------------------------------------------------------
    # Milestone execution
    # ------------------------------------------------------------------

    def _run_milestone(self, ctx: ProjectContext, milestone_id: str) -> ProjectContext:
        """Run a single milestone: BUILD → TEST+SECURITY → fix loops → APPROVED."""
        # Reset security retry counter per milestone
        ctx.retries["security"] = 0
        ctx.retries["test"] = 0

        # Reset security agent demo counter so fixture sequence restarts
        try:
            from security.security_agent import reset_demo_counter
            reset_demo_counter()
        except ImportError:
            pass

        # ---------------------------------------------------------------
        # BUILD
        # ---------------------------------------------------------------
        self._set_status(ctx, ProjectStatus.BUILDING)
        build_result = self._invoke_agent(
            "builder_agent",
            self.builder_fn,
            {"milestone_id": milestone_id},
        )
        ctx.agent_results.append(build_result)
        code_snapshot = build_result.get("payload", {}).get("files", [])

        # ---------------------------------------------------------------
        # TEST + SECURITY (parallel)
        # ---------------------------------------------------------------
        self._set_status(ctx, ProjectStatus.TESTING)
        tester_input   = {"milestone_id": milestone_id, "files": code_snapshot}
        security_input = {"milestone_id": milestone_id, "files": code_snapshot}

        test_result, security_result = run_parallel_sync(
            self.tester_fn, self.security_fn,
            tester_input, security_input,
        )
        ctx.agent_results.extend([test_result, security_result])

        merged = merge(test_result, security_result)

        # ---------------------------------------------------------------
        # Fix loops
        # ---------------------------------------------------------------
        while merged["verdict"] != "PASS":
            verdict = merged["verdict"]

            if verdict == "FIX_TEST":
                # Debugger loop
                ctx.retries["test"] += 1
                if ctx.retries["test"] > MAX_TEST_RETRIES:
                    return self._escalate(ctx, f"Test gate failed after {MAX_TEST_RETRIES} debug cycles")

                self._set_status(ctx, ProjectStatus.DEBUGGING)
                debug_result = self._invoke_agent(
                    "debugger_agent",
                    self.debugger_fn,
                    {
                        "milestone_id": milestone_id,
                        "failing_tests": test_result.get("payload", {}).get("test_results", []),
                        "files": code_snapshot,
                    },
                )
                ctx.agent_results.append(debug_result)
                # After patch, re-run both agents
                self._set_status(ctx, ProjectStatus.TESTING)

            elif verdict in ("FIX_SECURITY", "FIX_BOTH"):
                # Security-fix loop
                ctx.retries["security"] += 1
                if ctx.retries["security"] > MAX_SECURITY_RETRIES:
                    return self._escalate(
                        ctx,
                        f"Security gate BLOCKED after {MAX_SECURITY_RETRIES} fix attempts | "
                        f"milestone={milestone_id}",
                    )

                self._set_status(ctx, ProjectStatus.SECURITY_FIX)
                logger.info(
                    "Security fix requested | milestone=%s retry=%d/%d",
                    milestone_id,
                    ctx.retries["security"],
                    MAX_SECURITY_RETRIES,
                )
                fix_result = self._invoke_agent(
                    "builder_agent",
                    self.builder_fn,
                    {
                        "milestone_id": milestone_id,
                        "mode": "security_fix",
                        "findings": security_result.get("payload", {}).get("findings", []),
                        "files": code_snapshot,
                    },
                )
                ctx.agent_results.append(fix_result)
                # After security patch, re-run BOTH agents
                self._set_status(ctx, ProjectStatus.TESTING)

            # Re-run both agents (always — per architecture §6 and §4 security-fix loop)
            test_result, security_result = run_parallel_sync(
                self.tester_fn, self.security_fn,
                {"milestone_id": milestone_id, "files": code_snapshot},
                {"milestone_id": milestone_id, "files": code_snapshot},
            )
            ctx.agent_results.extend([test_result, security_result])
            merged = merge(test_result, security_result)

        # ---------------------------------------------------------------
        # MILESTONE APPROVED
        # ---------------------------------------------------------------
        self._set_status(ctx, ProjectStatus.MILESTONE_APPROVED)
        logger.info("Milestone approved | milestone=%s", milestone_id)
        return ctx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _invoke_agent(
        self,
        name: str,
        fn: Callable[[Dict], Dict],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info("Invoking agent | agent=%s", name)
        try:
            result = fn(input_data)
            logger.info("Agent finished | agent=%s status=%s", name, result.get("status"))
            return result
        except Exception as exc:
            logger.exception("Agent %s raised exception: %s", name, exc)
            return {
                "agent": name,
                "milestone_id": input_data.get("milestone_id", "unknown"),
                "status": "ERROR",
                "summary": f"Agent crashed: {exc}",
                "payload": {"error": str(exc)},
            }

    def _set_status(self, ctx: ProjectContext, status: str) -> None:
        old = ctx.status
        ctx.status = status
        logger.info(
            "Status transition | project=%s %s → %s",
            ctx.project_id,
            old,
            status,
        )
        if self.on_status_change:
            try:
                self.on_status_change(ctx.project_id, status)
            except Exception as exc:
                logger.warning("on_status_change callback failed: %s", exc)

    def _escalate(self, ctx: ProjectContext, reason: str) -> ProjectContext:
        logger.warning("Escalating to HUMAN_REVIEW | project=%s reason=%s", ctx.project_id, reason)
        self._set_status(ctx, ProjectStatus.HUMAN_REVIEW)
        ctx.agent_results.append({
            "agent": "orchestrator",
            "milestone_id": f"ms_{ctx.current_milestone_index:03d}",
            "status": "HUMAN_REVIEW",
            "summary": reason,
            "payload": {"reason": reason},
        })
        return ctx
