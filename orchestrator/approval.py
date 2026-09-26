"""
orchestrator/approval.py
Human approval step.

CLI usage:  request_approval_cli(context, gate_results) → bool
Backend usage: approve(project_id, approved=True/False) modifies the state file.
"""

from __future__ import annotations

from orchestrator.contracts import GateResult, ProjectContext


def _format_gate_results(gate_results: list[GateResult]) -> str:
    lines = []
    for gr in gate_results:
        icon = "✅" if gr.verdict.value == "PASS" else ("🔴" if gr.verdict.value == "BLOCKED" else "⚠")
        lines.append(f"  {icon} {gr.gate.value.upper():12s} {gr.verdict.value:8s}  {gr.reason}")
    return "\n".join(lines) if lines else "  (no gate results yet)"


def request_approval_cli(
    context: ProjectContext,
    gate_results: list[GateResult],
    prompt_text: str = "Approve and continue?",
    auto_approve: bool = False,
) -> bool:
    """
    Print a summary and ask the human y/n.
    Pass auto_approve=True to skip the prompt (for tests and CI).
    Returns True if approved, False otherwise.
    """
    print("\n" + "═" * 60)
    print(f"  ⏳ HUMAN APPROVAL REQUIRED")
    print(f"  Project : {context.project_id}")
    print(f"  Idea    : {context.idea}")
    print(f"\n  Gate results:")
    print(_format_gate_results(gate_results))
    print("═" * 60)

    if auto_approve:
        print("  [auto-approve=True] Approved automatically.")
        return True

    while True:
        try:
            answer = input(f"\n  {prompt_text} [y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Input stream closed — treating as rejection.")
            return False
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please enter y or n.")
