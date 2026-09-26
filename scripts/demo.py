"""
scripts/demo.py  -  the offline terminal demo (backup if the dashboard fails).

Runs the whole DevForge pipeline with the real agents and narrates each step with a
heading, so it can be presented live. No internet is needed.

    python scripts/demo.py                    # interactive: you answer the 2 approvals
    python scripts/demo.py --auto-approve     # no prompts (rehearsal / recording)
    python scripts/demo.py --pause 0          # no waiting between steps
    python scripts/demo.py --stub             # force every agent to its stub
    python scripts/demo.py --no-memory        # do not write into memory/ and metrics

The planted bugs in backend/demo_bug.py are restored before the run and again at the end,
so the demo can be repeated as often as you like.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # the config uses relative paths

IDEA = "task management SaaS"

# What we say when the pipeline enters each state.
NARRATION = {
    "PLANNING": ("1. PLAN", "Research, requirements and architecture are produced, then checked by the plan gate."),
    "BUILDING": ("2. BUILD", "The first milestone is built: the task API with ownership checks."),
    "TESTING": ("3. TEST + SECURITY", "Tests and the security scan run in parallel. Each result goes through its quality gate."),
    "DEBUGGING": ("4. DEBUG", "Tests failed, so the Debugger finds the root cause, patches the code and we test again."),
    "SECURITY_FIX": ("5. SECURITY FIX", "The security gate is BLOCKED, so the fix agent patches the finding and we rescan."),
    "SECURED": ("6. ALL GATES PASSED", "Tests 100% and no critical or high findings."),
    "AWAITING_APPROVAL": ("7. HUMAN APPROVAL", "Only a human can release. The gate results are shown below."),
    "RELEASED": ("8. RELEASED", "Approved by a human, so the project is released."),
    "FAILED": ("STOPPED", "Retry limit reached or a human rejected: escalated to a human."),
}


def banner(title: str, text: str = "") -> None:
    print("\n" + "=" * 64)
    print(f"  {title}")
    if text:
        print(f"  {text}")
    print("=" * 64, flush=True)


def install_narration(pause: float) -> None:
    """Add a heading and a short pause whenever the pipeline changes state."""
    from orchestrator.logger import OrchestratorLogger

    original = OrchestratorLogger._write
    seen: set[str] = set()

    def _write(self, payload: dict) -> None:
        if payload.get("event") == "STATE_TRANSITION" and payload.get("to") in NARRATION:
            title, text = NARRATION[payload["to"]]
            if payload["to"] == "TESTING" and "TESTING" in seen:
                title, text = "RE-TEST", "Tests and the security scan run again on the patched code."
            seen.add(payload["to"])
            banner(title, text)
            if pause:
                time.sleep(pause)
        original(self, payload)

    OrchestratorLogger._write = _write


def restore_bugs() -> None:
    from tests.restore_demo_bug import restore_demo_bug

    restore_demo_bug()


def summary(ctx) -> None:
    banner("DevForge result")
    print(f"  Status           : {ctx.status.value}")
    print(f"  Milestones       : {[(m.id, m.status.value) for m in ctx.milestones]}")
    print(f"  Retries          : {ctx.retries}")
    print(f"  Arch approved    : {ctx.human_approved_arch}")
    print(f"  Release approved : {ctx.human_approved_release}")
    last = ctx.last_test_result or {}
    data = last.get("data", {})
    if data:
        print(f"  Last test run    : {data.get('passed')}/{data.get('total')} passed")
    print("=" * 64)


def main() -> int:
    p = argparse.ArgumentParser(description="DevForge offline demo")
    p.add_argument("--idea", default=IDEA)
    p.add_argument("--auto-approve", action="store_true", help="skip the two y/n prompts")
    p.add_argument("--pause", type=float, default=2.0, help="seconds to wait between steps")
    p.add_argument("--stub", action="store_true", help="use the stub agents everywhere")
    p.add_argument("--no-memory", action="store_true", help="do not record memory/metrics")
    args = p.parse_args()

    if args.stub:
        for name in ("PLAN", "TEST", "DEBUG", "SECURITY"):
            os.environ[f"DEVFORGE_{name}_AGENT_MODE"] = "stub"
    if args.no_memory:
        os.environ["DEVFORGE_MEMORY"] = "off"

    from orchestrator.runner import run_pipeline  # imported after the env vars are set

    banner("DevForge", "AI Software Development Lifecycle Orchestrator")
    print(f"  Idea: {args.idea}")
    print("  Idea > Plan > Build > Test > Debug > Security > Fix > Human approval > Release")

    restore_bugs()
    install_narration(args.pause)
    try:
        ctx = run_pipeline(idea=args.idea, auto_approve=args.auto_approve, demo_mode=True)
    finally:
        restore_bugs()  # the real debug agent patched the demo file: put the bug back
    summary(ctx)
    return 0 if ctx.status.value == "RELEASED" else 1


if __name__ == "__main__":
    sys.exit(main())
