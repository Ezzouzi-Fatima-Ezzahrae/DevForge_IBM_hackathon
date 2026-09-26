"""
orchestrator/runner.py
Main pipeline loop.

Drives ProjectContext through the state machine, calls agents via the
registry, evaluates gates, handles retries, and invokes the human
approval step.  After BUILD, testing and security run in parallel via
a ThreadPoolExecutor.

Public API:
    run_pipeline(idea, project_id, auto_approve, demo_mode) -> ProjectContext
"""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator import agents_base
from orchestrator.approval import request_approval_cli
from orchestrator.contracts import (
    AgentResult,
    GateResult,
    GateVerdict,
    Milestone,
    MilestoneStatus,
    ProjectContext,
    ProjectStatus,
)
from orchestrator.gates import (
    evaluate_plan_gate,
    evaluate_release_gate,
    evaluate_security_gate,
    evaluate_test_gate,
)
from orchestrator.logger import get_logger
from orchestrator.state_machine import InvalidTransitionError, StateMachine


# ─── State persistence ────────────────────────────────────────────────────────

def _load_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "config" / "orchestrator_config.json"
    with open(cfg_path) as f:
        return json.load(f)


def _save_state(context: ProjectContext) -> None:
    cfg = _load_config()
    state_path = Path(cfg["state_file"])
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(context.model_dump(), f, indent=2, default=str)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_agent(stage: str, context: ProjectContext) -> AgentResult:
    logger = get_logger()
    agent = agents_base.get_agent(stage)
    logger.agent_start(context.project_id, agent.__class__.__name__, stage)
    result = agent.run(context)
    logger.agent_done(
        context.project_id,
        result.agent,
        stage,
        result.status.value,
        result.duration_seconds,
        result.summary,
    )
    return result


def _transition(
    sm: StateMachine,
    context: ProjectContext,
    target: ProjectStatus,
) -> None:
    logger = get_logger()
    old = sm.state.value
    sm.advance(target)
    context.status = sm.state
    logger.transition(context.project_id, old, target.value)
    _save_state(context)


# ─── Parallel quality checks ──────────────────────────────────────────────────

def _parallel_test_and_security(
    context: ProjectContext,
    milestone_id: str,
) -> tuple[AgentResult, AgentResult]:
    """
    Run tester and security agents concurrently.
    Returns (test_result, security_result).
    """
    results: dict[str, AgentResult] = {}

    def run_stage(stage: str) -> tuple[str, AgentResult]:
        return stage, _run_agent(stage, context)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(run_stage, s): s for s in ("test", "security")}
        for future in as_completed(futures):
            stage, result = future.result()
            results[stage] = result

    return results["test"], results["security"]


# ─── Main pipeline ────────────────────────────────────────────────────────────

def run_pipeline(
    idea: str,
    project_id: str | None = None,
    auto_approve: bool = False,
    demo_mode: bool = True,
) -> ProjectContext:
    """
    Run the full DevForge pipeline for *idea*.

    Parameters
    ----------
    idea          : The raw idea string from the user.
    project_id    : Optional fixed ID (generated if None).
    auto_approve  : Skip CLI prompts (for tests / CI).
    demo_mode     : If True stubs will FAIL first then PASS (shows the debug/fix loops).

    Returns the final ProjectContext.
    """
    cfg = _load_config()
    project_id = project_id or f"proj_{uuid.uuid4().hex[:8]}"
    logger = get_logger(cfg["log_file"])

    context = ProjectContext(
        project_id=project_id,
        idea=idea,
        status=ProjectStatus.IDLE,
        created_at=_now(),
    )
    sm = StateMachine(ProjectStatus.IDLE)
    gate_results: list[GateResult] = []

    # If not demo_mode, configure stubs to always pass
    if not demo_mode:
        try:
            tester = agents_base.get_agent("test")
            if hasattr(tester, "fail_first"):
                tester.fail_first = False
            security = agents_base.get_agent("security")
            if hasattr(security, "fail_first"):
                security.fail_first = False
        except KeyError:
            pass

    logger.info(project_id, f"Pipeline started for idea: '{idea}'")

    # ── PLANNING ───────────────────────────────────────────────────────────────
    _transition(sm, context, ProjectStatus.PLANNING)
    max_plan_retries: int = cfg["retries"].get("plan_max", 2)
    plan_gate_result: GateResult | None = None

    for plan_attempt in range(max_plan_retries + 1):
        plan_result = _run_agent("plan", context)
        plan_gate_result = evaluate_plan_gate(plan_result, context)
        logger.gate(
            project_id, "plan",
            plan_gate_result.verdict.value,
            plan_gate_result.reason,
            plan_attempt,
        )
        gate_results.append(plan_gate_result)

        if plan_gate_result.verdict == GateVerdict.PASS:
            break
        context.retries["plan"] = plan_attempt + 1
        if plan_attempt == max_plan_retries:
            logger.escalation(project_id, "plan", plan_gate_result.reason)
            _transition(sm, context, ProjectStatus.FAILED)
            return context
        logger.retry(project_id, "plan", plan_attempt + 1, max_plan_retries)

    # Architecture human approval
    arch_approved = request_approval_cli(
        context,
        [plan_gate_result],
        prompt_text="Approve architecture and proceed to build?",
        auto_approve=auto_approve,
    )
    logger.human_approval(project_id, "architecture", arch_approved)
    if not arch_approved:
        _transition(sm, context, ProjectStatus.FAILED)
        return context
    context.human_approved_arch = True

    # Build milestones list (inlined planner — 1 milestone for MVP)
    context.milestones = [
        Milestone(
            id="ms_001",
            title="Task CRUD API",
            description="POST /tasks, GET /tasks, PATCH /tasks/{id}, DELETE /tasks/{id} with ownership checks",
            order=1,
            requirement_ids=["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"],
        )
    ]
    _save_state(context)

    # ── MILESTONE LOOP ─────────────────────────────────────────────────────────
    test_max  = cfg["retries"]["test_max"]
    sec_max   = cfg["retries"]["security_max"]

    for ms_index, milestone in enumerate(context.milestones):
        context.current_milestone_index = ms_index
        milestone.status = MilestoneStatus.BUILDING
        logger.info(project_id, f"Starting milestone {ms_index + 1}: {milestone.title}")

        # ── BUILD ──────────────────────────────────────────────────────────────
        _transition(sm, context, ProjectStatus.BUILDING)
        _run_agent("build", context)
        milestone.status = MilestoneStatus.TESTING
        _save_state(context)

        # ── PARALLEL: TEST + SECURITY ──────────────────────────────────────────
        _transition(sm, context, ProjectStatus.TESTING)
        test_retry = 0
        sec_retry  = 0

        # Reset stubs for each milestone
        try:
            tester = agents_base.get_agent("test")
            if hasattr(tester, "reset"):
                tester.reset()
            security = agents_base.get_agent("security")
            if hasattr(security, "reset"):
                security.reset()
        except KeyError:
            pass

        # Outer loop: test might fail → debug; security might fail → fix
        while True:
            test_result, sec_result = _parallel_test_and_security(context, milestone.id)
            context.last_test_result = test_result.model_dump()
            
            test_gate  = evaluate_test_gate(test_result, context, milestone.id)
            sec_gate   = evaluate_security_gate(sec_result, context, milestone.id)
            logger.gate(project_id, "tests", test_gate.verdict.value, test_gate.reason, test_retry)
            logger.gate(project_id, "security", sec_gate.verdict.value, sec_gate.reason, sec_retry)
            gate_results.extend([test_gate, sec_gate])

            # ── Test FAIL → Debug ──────────────────────────────────────────────
            if test_gate.verdict != GateVerdict.PASS:
                if test_retry >= test_max:
                    logger.escalation(project_id, "test", test_gate.reason)
                    _transition(sm, context, ProjectStatus.FAILED)
                    milestone.status = MilestoneStatus.FAILED
                    return context
                test_retry += 1
                context.retries["test"] = test_retry
                logger.retry(project_id, "test", test_retry, test_max)
                _transition(sm, context, ProjectStatus.DEBUGGING)
                _run_agent("debug", context)
                # Security ran in parallel and may ALSO have blocked: fix it in
                # the same round so no finding is silently skipped.
                if sec_gate.verdict != GateVerdict.PASS:
                    if sec_retry >= sec_max:
                        logger.escalation(project_id, "security", sec_gate.reason)
                        _transition(sm, context, ProjectStatus.FAILED)
                        milestone.status = MilestoneStatus.FAILED
                        return context
                    sec_retry += 1
                    context.retries["security"] = sec_retry
                    logger.retry(project_id, "security", sec_retry, sec_max)
                    _transition(sm, context, ProjectStatus.SECURITY_FIX)
                    _run_agent("fix", context)
                _transition(sm, context, ProjectStatus.TESTING)
                continue  # rerun both in parallel

            # ── Test PASS, Security FAIL → Fix ─────────────────────────────────
            if sec_gate.verdict != GateVerdict.PASS:
                if sec_retry >= sec_max:
                    logger.escalation(project_id, "security", sec_gate.reason)
                    _transition(sm, context, ProjectStatus.FAILED)
                    milestone.status = MilestoneStatus.FAILED
                    return context
                sec_retry += 1
                context.retries["security"] = sec_retry
                logger.retry(project_id, "security", sec_retry, sec_max)
                _transition(sm, context, ProjectStatus.SECURITY_FIX)
                _run_agent("fix", context)
                _transition(sm, context, ProjectStatus.TESTING)
                continue  # rerun both

            # ── Both PASS ──────────────────────────────────────────────────────
            break

        _transition(sm, context, ProjectStatus.SECURED)
        milestone.status = MilestoneStatus.APPROVED
        logger.info(project_id, f"Milestone {ms_index + 1} APPROVED ✅")
        _save_state(context)

    # ── HUMAN RELEASE APPROVAL ─────────────────────────────────────────────────
    _transition(sm, context, ProjectStatus.AWAITING_APPROVAL)
    release_gate = evaluate_release_gate(context)
    gate_results.append(release_gate)

    release_approved = request_approval_cli(
        context,
        gate_results,
        prompt_text="All gates passed. Approve release?",
        auto_approve=auto_approve,
    )
    logger.human_approval(project_id, "release", release_approved)

    if not release_approved:
        context.human_approved_release = False
        _transition(sm, context, ProjectStatus.BUILDING)
        logger.info(project_id, "Release rejected — returning to build stage")
        _save_state(context)
        return context

    context.human_approved_release = True
    _transition(sm, context, ProjectStatus.RELEASED)
    logger.info(project_id, "🚀 Pipeline complete — project RELEASED")
    _save_state(context)
    return context
