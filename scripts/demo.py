"""
scripts/demo.py  -  the narrated terminal demo (also the backup if the dashboard fails).

Runs the whole DevForge pipeline with the real agents and shows every step in colour:
pipeline tracker, test bars, the real security finding, the real code patch (diff),
quality gates, the human approval panel and a final result card. No internet needed.

    python scripts/demo.py                    # interactive: you answer the 2 approvals (best for a recording)
    python scripts/demo.py --auto-approve     # no prompts
    python scripts/demo.py --fast             # no pauses or typing effect (rehearsal)
    python scripts/demo.py --pause 2.5        # slower, more time to talk
    python scripts/demo.py --plain            # no colours (old terminals, logs)
    python scripts/demo.py --stub             # force every agent to its stub
    python scripts/demo.py --no-memory        # do not write into memory/ and metrics

Tip: use Windows Terminal or PowerShell, a dark background and a big font (Ctrl + mouse wheel).
The planted bug in backend/demo_bug.py is restored before the run and again at the end,
so the demo can be repeated as often as you like.
"""
from __future__ import annotations

import argparse
import contextlib
import difflib
import io
import os
import re
import sys
import textwrap
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # the config uses relative paths

IDEA = "task management SaaS"
WIDTH = 78

# ─── terminal helpers ─────────────────────────────────────────────────────────

COLOR = True
PACE = 1.0  # 0 = no waiting at all


def _setup_terminal() -> None:
    if os.name == "nt":
        os.system("")  # switches on ANSI colours in the Windows console
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass


def c(text: str, code: int | str, bold: bool = False, dim: bool = False) -> str:
    """Colour with a 256-colour code."""
    if not COLOR:
        return text
    pre = ("\033[1m" if bold else "") + ("\033[2m" if dim else "") + f"\033[38;5;{code}m"
    return f"{pre}{text}\033[0m"


ORANGE, EMBER, GOLD = 208, 202, 214
GREEN, RED, YELLOW = 78, 203, 221
CYAN, STEEL, WHITE, GREY = 80, 246, 255, 240

_ANSI = re.compile(r"\033\[[0-9;]*m")


def vlen(s: str) -> int:
    return len(_ANSI.sub("", s))


def out(s: str = "") -> None:
    print(s, flush=True)


def wait(seconds: float) -> None:
    if PACE > 0 and seconds > 0:
        time.sleep(seconds * PACE)


def typed(text: str, code: int | str = WHITE, delay: float = 0.012, indent: str = "  ") -> None:
    """Typewriter effect for the narration."""
    if PACE == 0 or not sys.stdout.isatty():
        out(indent + c(text, code))
        return
    sys.stdout.write(indent)
    for ch in text:
        sys.stdout.write(c(ch, code) if COLOR else ch)
        sys.stdout.flush()
        time.sleep(delay * PACE)
    sys.stdout.write("\n")


def box(title: str, lines: list[str], color: int | str = ORANGE, width: int = WIDTH) -> None:
    inner = width - 2
    t = f" {title} "
    out(c("╔" + "═" * 2 + t + "═" * max(0, inner - 2 - len(t)) + "╗", color, bold=True))
    for ln in lines:
        pad = max(0, inner - 1 - vlen(ln))
        out(c("║", color) + " " + ln + " " * pad + c("║", color))
    out(c("╚" + "═" * inner + "╝", color, bold=True))


def bar(passed: int, total: int, width: int = 20) -> str:
    filled = round(width * passed / total) if total else 0
    color = GREEN if passed == total else RED
    return c("█" * filled, color) + c("░" * (width - filled), GREY) + " " + c(f"{passed}/{total}", color, bold=True)


# ─── banner ───────────────────────────────────────────────────────────────────

_FONT = {
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "V": ["██╗   ██╗", "██║   ██║", "██║   ██║", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚═══╝  "],
    "F": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "██║     ", "╚═╝     "],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    "G": [" ██████╗ ", "██╔════╝ ", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
}
_GRADIENT = [226, 220, 214, 208, 202, 196]


def banner() -> None:
    out()
    for row in range(6):
        line = "".join(_FONT[ch][row].ljust(len(max(_FONT[ch], key=len))) + " " for ch in "DEVFORGE"[:0] or "DEVFORGE")
        out("  " + c(line, _GRADIENT[row], bold=True))
        wait(0.06)
    out()
    typed("AI Software Development Lifecycle Orchestrator", ORANGE, indent="  ")
    out("  " + c("Idea  ▸  Plan  ▸  Build  ▸  Test  ▸  Debug  ▸  Security  ▸  Fix  ▸  Human approval  ▸  Release", STEEL))
    out("  " + c("━" * (WIDTH - 2), GREY))


# ─── pipeline tracker ─────────────────────────────────────────────────────────

STEPS = ["plan", "build", "test", "debug", "security", "fix", "approve", "release"]
step_state = {s: "pending" for s in STEPS}


def tracker() -> None:
    parts = []
    for s in STEPS:
        st = step_state[s]
        label = s.upper()
        if st == "done":
            parts.append(c("✔ " + label, GREEN, bold=True))
        elif st == "failed":
            parts.append(c("✘ " + label, RED, bold=True))
        elif st == "active":
            parts.append(c("◉ " + label, ORANGE, bold=True))
        else:
            parts.append(c("○ " + label, GREY))
    out("  " + c(" ─ ", GREY).join(parts))


# ─── narration per state ──────────────────────────────────────────────────────

NARRATION = {
    "PLANNING": ("1  PLAN", "Requirements, architecture and decisions, checked by the plan gate."),
    "BUILDING": ("2  BUILD", "Milestone 1 is built: the task API with ownership checks."),
    "TESTING": ("3  TEST  +  SECURITY", "Tests and the security scan run in parallel. Each result meets a quality gate."),
    "DEBUGGING": ("4  DEBUG", "Tests failed. The Debugger finds the root cause, patches the code, and we test again."),
    "SECURITY_FIX": ("5  SECURITY FIX", "The security gate is BLOCKED. The fix step runs, then we rescan."),
    "SECURED": ("6  ALL GATES PASSED", "Tests 100% and no critical or high finding."),
    "AWAITING_APPROVAL": ("7  HUMAN APPROVAL", "Only a human can release."),
    "RELEASED": ("8  RELEASED", "Approved by a human. The project is released."),
    "FAILED": ("STOPPED", "Retry limit reached or a human rejected: escalated to a human."),
}
ACTIVE_ON = {"PLANNING": ["plan"], "BUILDING": ["build"], "TESTING": ["test", "security"], "DEBUGGING": ["debug"],
             "SECURITY_FIX": ["fix"], "AWAITING_APPROVAL": ["approve"]}
STAGE_TO_STEP = {"plan": "plan", "build": "build", "test": "test", "debug": "debug", "security": "security", "fix": "fix"}

# what the run looked like, for the final card
facts = {"tests": [], "security": [], "start": 0.0, "approvals": 0, "agents": {}, "seen_testing": False}


def section(state: str) -> None:
    title, text = NARRATION[state]
    if state == "TESTING" and facts["seen_testing"]:
        title, text = "RE-TEST", "Tests and the security scan run again on the patched code."
    if state == "TESTING":
        facts["seen_testing"] = True
    color = RED if state == "FAILED" else (GREEN if state in ("SECURED", "RELEASED") else ORANGE)
    for step in ACTIVE_ON.get(state, []):
        if step_state[step] != "done":
            step_state[step] = "active"
    out()
    out("  " + c(f" {title} ", 16, bold=True).replace("\033[38;5;16m", f"\033[48;5;{color}m\033[38;5;16m") if COLOR else f"  [ {title} ]")
    typed(text, STEEL)
    tracker()
    out()
    wait(1.1)


def tag_for(agent_class: str) -> str:
    if "Stub" in agent_class:
        return c(" STUB ", 16, bold=True).replace("\033[38;5;16m", "\033[48;5;221m\033[38;5;16m") if COLOR else "[STUB]"
    if agent_class == "PlanAgent":
        return c(" REPLAY ", 16, bold=True).replace("\033[38;5;16m", "\033[48;5;80m\033[38;5;16m") if COLOR else "[REPLAY]"
    return c(" REAL ", 16, bold=True).replace("\033[38;5;16m", "\033[48;5;78m\033[38;5;16m") if COLOR else "[REAL]"


def show_patch() -> None:
    """Show the real change the Debugger just made to backend/demo_bug.py."""
    try:
        before = (ROOT / "tests" / "fixtures" / "demo_bug_original.py").read_text(encoding="utf-8").splitlines()
        after = (ROOT / "backend" / "demo_bug.py").read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    diff = [d for d in difflib.unified_diff(before, after, "before", "after", lineterm="", n=1)]
    if not diff:
        return
    out("     " + c("┌─ patch applied to backend/demo_bug.py", STEEL))
    for d in diff[2:]:
        if d.startswith("@@"):
            continue
        if d.startswith("+"):
            out("     " + c("│ ", STEEL) + c(d, GREEN))
        elif d.startswith("-"):
            out("     " + c("│ ", STEEL) + c(d, RED))
        else:
            out("     " + c("│ " + d, GREY))
    out("     " + c("└─", STEEL))
    wait(1.0)


def show_finding(summary: str) -> None:
    m = re.search(r"\[(CWE-\d+)\]\s*(.*?)\s*\(([^()]*:\d+)\)", summary)
    if not m:
        return
    cwe, desc, where = m.groups()
    out("     " + c("┌─ security finding", STEEL))
    names = {"CWE-639": "broken access control", "CWE-798": "hard-coded credentials"}
    sev = c(" HIGH ", 16, bold=True).replace("\033[38;5;16m", "\033[48;5;203m\033[38;5;16m") if COLOR else "[HIGH]"
    out("     " + c("│ ", STEEL) + sev + " " + c(cwe, WHITE, bold=True) + c("  " + names.get(cwe, ""), WHITE))
    out("     " + c("│ ", STEEL) + c(where, CYAN))
    for part in textwrap.wrap(desc, 62)[:2]:
        out("     " + c("│ ", STEEL) + c(part, STEEL))
    out("     " + c("└─", STEEL))
    wait(1.0)


# ─── log events → styled lines ────────────────────────────────────────────────

def render(p: dict) -> None:
    ev = p.get("event")
    if ev == "STATE_TRANSITION":
        to = p.get("to")
        if to == "RELEASED":
            step_state["release"] = "done"
        if to in NARRATION:
            section(to)
    elif ev == "AGENT_START":
        stage = p.get("stage")
        step = STAGE_TO_STEP.get(stage)
        if step:
            step_state[step] = "active"
        facts["agents"][stage] = p.get("agent", "")
        out("   " + c("▸", ORANGE) + " " + c(f"{stage.upper():<9}", WHITE, bold=True) + tag_for(p.get("agent", "")) + " " + c("running…", GREY))
        wait(0.35)
    elif ev == "AGENT_DONE":
        stage, status = p.get("stage"), p.get("status")
        ok = status == "PASS"
        step = STAGE_TO_STEP.get(stage)
        if step:
            step_state[step] = "done" if ok else "failed"
        icon = c("✔", GREEN, bold=True) if ok else c("✘", RED, bold=True)
        summary = (p.get("summary") or "")
        short = summary if len(summary) <= 62 else summary[:59] + "..."
        if stage == "security" and not ok:
            short = "BLOCKED: 1 HIGH finding"
        out("   " + icon + " " + c(f"{stage.upper():<9}", WHITE, bold=True) + c(status, GREEN if ok else RED, bold=True) + c(f"  {p.get('duration_seconds', 0):.2f}s  ", GREY) + c(short, STEEL))
        if stage == "security" and not ok:
            show_finding(summary)
        if stage == "debug" and ok:
            show_patch()
        wait(0.5)
    elif ev == "GATE":
        gate, verdict, reason = p.get("gate", ""), p.get("verdict", ""), p.get("reason", "")
        ok = verdict == "PASS"
        badge = c(f" {gate.upper()} GATE ", 16, bold=True)
        badge = badge.replace("\033[38;5;16m", f"\033[48;5;{GREEN if ok else RED}m\033[38;5;16m") if COLOR else f"[{gate.upper()} GATE]"
        extra = ""
        m = re.search(r"(\d+)/(\d+)", reason)
        if gate == "tests" and m:
            passed, total = int(m.group(1)), int(m.group(2))
            facts["tests"].append((passed, total))
            extra = "  " + bar(passed, total)
        elif gate == "security":
            facts["security"].append(verdict)
            extra = "  " + c(verdict, GREEN if ok else RED, bold=True)
        elif gate == "plan":
            extra = "  " + c(reason, STEEL)
        else:
            extra = "  " + c(verdict, GREEN if ok else RED, bold=True)
        out("   " + badge + extra)
        wait(0.6)
    elif ev == "RETRY":
        out("   " + c("↻ retry ", YELLOW, bold=True) + c(f"{p.get('stage')}  {p.get('attempt')}/{p.get('max')}", YELLOW))
        wait(0.4)
    elif ev == "ESCALATION":
        out("   " + c("⚠ ESCALATION ", RED, bold=True) + c(p.get("reason", ""), RED))
    elif ev == "HUMAN_APPROVAL":
        facts["approvals"] += 1
        if p.get("gate") == "release":
            step_state["approve"] = "done" if p.get("approved") else "failed"
    elif ev == "ERROR":
        out("   " + c("✘ " + str(p.get("msg", "")), RED))


def install_logging() -> None:
    from orchestrator.logger import OrchestratorLogger

    original = OrchestratorLogger._write
    lock = threading.Lock()

    def _write(self, payload: dict) -> None:
        with lock:  # tests and security log from two threads: keep the output in order
            with contextlib.redirect_stdout(io.StringIO()):  # the log file is still written, the plain echo is hidden
                original(self, payload)
            render(payload)

    OrchestratorLogger._write = _write


# ─── human approval panel ─────────────────────────────────────────────────────

def make_approval_fn(auto: bool):
    def approve(context, gate_results, prompt_text="Approve and continue?", auto_approve=False) -> bool:
        history: dict[str, list[str]] = {}
        for g in gate_results:
            history.setdefault(g.gate.value, []).append(g.verdict.value)
        is_release = "release" in prompt_text.lower()
        if is_release:
            step_state["approve"] = "active"
        lines = [c(f"Project {context.project_id}", STEEL), c(f"Idea: {context.idea}", STEEL), ""]
        for gate, verdicts in history.items():
            final = verdicts[-1]
            ok = final == "PASS"
            if gate == "release":
                lines.append(c("… ", YELLOW) + c(f"{gate.upper():<10}", WHITE, bold=True) + c("awaiting your approval", YELLOW, bold=True))
                continue
            trail = c(" ▸ ", GREY).join(c(v, GREEN if v == "PASS" else RED, bold=(i == len(verdicts) - 1)) for i, v in enumerate(verdicts))
            lines.append((c("✔ ", GREEN, bold=True) if ok else c("… ", YELLOW)) + c(f"{gate.upper():<10}", WHITE, bold=True) + trail)
        out()
        box("HUMAN APPROVAL REQUIRED", lines, ORANGE)
        typed(prompt_text, WHITE)
        if auto or auto_approve:
            for i in range(3):
                sys.stdout.write("\r  " + c("waiting for the human" + "." * (i + 1) + "   ", GREY))
                sys.stdout.flush()
                wait(0.5)
            out("\r  " + c("✔ APPROVED", GREEN, bold=True) + c(" (auto-approve)", GREY) + " " * 20)
            return True
        while True:
            try:
                answer = input("  " + c("Approve? [y/n] ▸ ", ORANGE, bold=True)).strip().lower()
            except (EOFError, KeyboardInterrupt):
                out("  " + c("input closed: treated as a rejection", RED))
                return False
            if answer in ("y", "yes"):
                out("  " + c("✔ APPROVED by the human", GREEN, bold=True))
                return True
            if answer in ("n", "no"):
                out("  " + c("✘ REJECTED by the human", RED, bold=True))
                return False

    return approve


# ─── final card ───────────────────────────────────────────────────────────────

def summary_card(ctx, seconds: float) -> None:
    released = ctx.status.value == "RELEASED"
    color = GREEN if released else RED
    lines = [
        "",
        c(("  ✔  PROJECT RELEASED" if released else f"  ✘  {ctx.status.value}"), color, bold=True),
        "",
    ]
    t = facts["tests"]
    if t:
        first, last = t[0], t[-1]
        lines.append(c("Tests      ", STEEL) + bar(*first, 12) + c("  ▸  ", GREY) + bar(*last, 12))
    s = facts["security"]
    if s:
        first, last = s[0], s[-1]
        lines.append(c("Security   ", STEEL) + c(first, GREEN if first == "PASS" else RED, bold=True) + c("  ▸  ", GREY) + c(last, GREEN if last == "PASS" else RED, bold=True))
    r = ctx.retries
    lines.append(c("Retries    ", STEEL) + c(f"tests {r.get('test', 0)}   security {r.get('security', 0)}   plan {r.get('plan', 0)}", WHITE))
    lines.append(c("Humans     ", STEEL) + c(f"{facts['approvals']} approvals (architecture, release)", WHITE))
    lines.append(c("Time       ", STEEL) + c(f"{seconds:.1f} s", WHITE))
    lines.append("")
    kinds = []
    for stage in ("plan", "build", "test", "debug", "security", "fix"):
        agent = facts["agents"].get(stage, "")
        label = "stub" if "Stub" in agent else ("replay" if agent == "PlanAgent" else "real")
        kinds.append(f"{stage} " + c(f"({label})", GREEN if label == "real" else YELLOW))
    lines.append(c("Agents     ", STEEL) + "  ".join(kinds[:3]))
    lines.append(c("           ", STEEL) + "  ".join(kinds[3:]))
    lines.append("")
    out()
    box("DEVFORGE RESULT", lines, color)
    out()


# ─── main ─────────────────────────────────────────────────────────────────────

def restore_bugs() -> None:
    from tests.restore_demo_bug import restore_demo_bug

    restore_demo_bug()


def main() -> int:
    global COLOR, PACE
    p = argparse.ArgumentParser(description="DevForge narrated demo")
    p.add_argument("--idea", default=IDEA)
    p.add_argument("--auto-approve", action="store_true", help="skip the two y/n prompts")
    p.add_argument("--pause", type=float, default=1.0, help="speed factor for the pauses (1 = normal, 2 = slower)")
    p.add_argument("--fast", action="store_true", help="no pauses and no typing effect")
    p.add_argument("--plain", action="store_true", help="no colours")
    p.add_argument("--color", action="store_true", help="force colours even when not in a terminal")
    p.add_argument("--stub", action="store_true", help="use the stub agents everywhere")
    p.add_argument("--no-memory", action="store_true", help="do not record memory/metrics")
    args = p.parse_args()

    _setup_terminal()
    PACE = 0.0 if args.fast else args.pause
    COLOR = (sys.stdout.isatty() or args.color) and not args.plain and "NO_COLOR" not in os.environ

    if args.stub:
        for name in ("PLAN", "TEST", "DEBUG", "SECURITY"):
            os.environ[f"DEVFORGE_{name}_AGENT_MODE"] = "stub"
    if args.no_memory:
        os.environ["DEVFORGE_MEMORY"] = "off"

    from orchestrator.runner import run_pipeline  # imported after the env vars are set

    restore_bugs()
    banner()
    out("  " + c("Idea", STEEL) + "  " + c(args.idea, WHITE, bold=True))
    out()
    wait(1.0)
    install_logging()
    facts["start"] = time.time()
    try:
        ctx = run_pipeline(idea=args.idea, auto_approve=args.auto_approve,
                           demo_mode=True, approval_fn=make_approval_fn(args.auto_approve))
    finally:
        restore_bugs()  # the real debug agent patched the demo file: put the bug back
    summary_card(ctx, time.time() - facts["start"])
    return 0 if ctx.status.value == "RELEASED" else 1


if __name__ == "__main__":
    sys.exit(main())
