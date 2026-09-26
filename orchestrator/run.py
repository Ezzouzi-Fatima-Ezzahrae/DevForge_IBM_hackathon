"""
orchestrator/run.py
CLI entry point.

Usage:
    python -m orchestrator.run --idea "task management SaaS"
    python -m orchestrator.run --idea "task management SaaS" --no-demo
    python -m orchestrator.run --idea "task management SaaS" --auto-approve
"""

from __future__ import annotations

import argparse
import sys

from orchestrator.runner import run_pipeline


def _print_summary(context) -> None:
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  DevForge Pipeline Summary")
    print(sep)
    print(f"  Project ID : {context.project_id}")
    print(f"  Idea       : {context.idea}")
    print(f"  Status     : {context.status.value}")
    print(f"  Milestones : {len(context.milestones)}")
    for ms in context.milestones:
        icon = "✅" if ms.status.value == "approved" else "🔴"
        print(f"    {icon}  [{ms.id}] {ms.title}  → {ms.status.value}")
    print(f"  Retries    : {context.retries}")
    print(f"  Arch approved    : {context.human_approved_arch}")
    print(f"  Release approved : {context.human_approved_release}")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(description="DevForge — AI SDLC Orchestrator")
    parser.add_argument("--idea", required=True, help="The project idea to orchestrate")
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip human approval prompts (for CI / tests)",
    )
    parser.add_argument(
        "--no-demo",
        action="store_true",
        help="Disable stub failure loops (stubs always pass)",
    )
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════════════════════╗")
    print(  "║       DevForge — AI Software Development Lifecycle       ║")
    print(  "╚══════════════════════════════════════════════════════════╝")
    print(f"  Idea: {args.idea}\n")

    context = run_pipeline(
        idea=args.idea,
        auto_approve=args.auto_approve,
        demo_mode=not args.no_demo,
    )
    _print_summary(context)

    exit_code = 0 if context.status.value == "RELEASED" else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
