"""
orchestrator/runner.py
Parallel agent dispatch + result merge — DevForge pipeline.

The runner launches Tester and Security Agent concurrently (asyncio.gather),
collects both AgentResults, and merges them into a combined verdict.

Merge rules (from ARCHITECTURE.md §6):
    Both PASS   → MILESTONE_APPROVED
    Both fail   → fix security first (higher risk, smaller patch surface)
    Only test   → Debugger loop, then re-run both
    Only sec    → SECURITY_FIX, then re-run both

After a SECURITY_FIX the runner always re-runs BOTH agents — not just security.
A security patch can introduce test regressions.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Async runner
# ---------------------------------------------------------------------------

async def run_parallel(
    tester_fn: Callable[[Dict], Any],
    security_fn: Callable[[Dict], Any],
    tester_input: Dict[str, Any],
    security_input: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Run tester and security agent concurrently.

    Args:
        tester_fn:       Callable that accepts a dict and returns an AgentResult dict.
        security_fn:     Callable that accepts a dict and returns an AgentResult dict.
        tester_input:    Input dict for the tester agent.
        security_input:  Input dict for the security agent.

    Returns:
        (tester_result, security_result) — both AgentResult dicts.
    """
    loop = asyncio.get_event_loop()

    # Run both agents in a thread pool to avoid blocking the event loop
    # (since agent implementations may call subprocess or do I/O).
    tester_task   = loop.run_in_executor(None, tester_fn,   tester_input)
    security_task = loop.run_in_executor(None, security_fn, security_input)

    tester_result, security_result = await asyncio.gather(
        tester_task,
        security_task,
    )

    logger.info(
        "Parallel run complete | tester=%s security=%s",
        tester_result.get("status"),
        security_result.get("status"),
    )
    return tester_result, security_result


def run_parallel_sync(
    tester_fn: Callable[[Dict], Any],
    security_fn: Callable[[Dict], Any],
    tester_input: Dict[str, Any],
    security_input: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Synchronous wrapper around run_parallel for callers that cannot use await.
    """
    return asyncio.run(
        run_parallel(tester_fn, security_fn, tester_input, security_input)
    )


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def merge(
    test_result: Dict[str, Any],
    security_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge the results of the Tester and Security Agent into a combined verdict.

    Returns a dict with:
        {
            "verdict": "PASS" | "FIX_TEST" | "FIX_SECURITY" | "FIX_BOTH",
            "test_status": "...",
            "security_status": "...",
            "test_result": {...},
            "security_result": {...},
        }

    Merge rules:
        Both PASS        → "PASS"
        Only test fails  → "FIX_TEST"   (Debugger loop)
        Only sec BLOCKED → "FIX_SECURITY" (SECURITY_FIX loop)
        Both fail        → "FIX_SECURITY" (fix security first per architecture)
        Security ERROR   → "FIX_SECURITY" (treat error as blocking — escalate)
    """
    test_status = test_result.get("status", "FAIL")
    sec_status  = security_result.get("status", "BLOCKED")

    test_pass = test_status == "PASS"
    sec_pass  = sec_status == "PASS"

    if test_pass and sec_pass:
        verdict = "PASS"
    elif test_pass and not sec_pass:
        verdict = "FIX_SECURITY"
    elif not test_pass and sec_pass:
        verdict = "FIX_TEST"
    else:
        # Both fail → architecture says fix security first
        verdict = "FIX_SECURITY"

    result = {
        "verdict": verdict,
        "test_status": test_status,
        "security_status": sec_status,
        "test_result": test_result,
        "security_result": security_result,
    }

    logger.info(
        "Merge result | test=%s security=%s verdict=%s",
        test_status,
        sec_status,
        verdict,
    )
    return result
