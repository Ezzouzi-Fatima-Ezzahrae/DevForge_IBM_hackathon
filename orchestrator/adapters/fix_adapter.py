"""
orchestrator/adapters/fix_adapter.py
Real Fix agent: patches whatever the Security stage actually found.

Why this exists
----------------
orchestrator/stubs/fix_stub.py always claims "[STUB] Security patch applied
to backend/routers/tasks.py:54" no matter what Security reported. That was
fine while Security was also a stub returning that exact fake finding, but
once Security runs for real (orchestrator/adapters/security_adapter.py) it
reports real findings at real locations -- and FixStub keeps "fixing" a file
that was never the problem, so the re-scan finds the same real issue again
and the security gate stays BLOCKED until retries run out.

This adapter reads context.last_security_result (populated by runner.py
right after the parallel test+security run) and, for each OPEN finding it
recognises, applies a real fix:

    secrets_exposure (CWE-798 / CWE-259, Bandit B105/B106/B107):
        Delegates to security.fix_agent.fix_hardcoded_secret, which already
        implements this correctly and has its own tests -- this adapter's
        only job is to translate the finding's file:line into that
        function's {file, line, var_name} contract by reading the variable
        name off the reported line.

    broken_access_control (CWE-639 / CWE-862):
        No equivalent real implementation exists yet, so this adapter
        applies its own best-effort AST-based patch: insert
        `if <resource>.owner_id != <current_user>.id: raise
        HTTPException(status_code=403)` right after the point in the
        function where both are already bound to a local variable. It first
        checks whether the function already has an ownership/403 check
        (the same heuristic security/scanner.py's own auth checker uses to
        decide a check is *absent*) so it never inserts a duplicate check
        next to one the Debug agent already added while repairing a failing
        test in the same retry round.

A finding type/CWE this adapter doesn't recognise is left untouched and
reported as not-fixed -- it never guesses at a patch it can't justify, and
the re-scan will simply fail the gate again with an honest reason rather
than the pipeline pretending it's clear.

Findings are applied in descending line-number order (within a file) so
that an earlier patch's `import os` insertion at the top of the file can
never shift a not-yet-processed finding's line number out from under it.

Never raises: any problem is caught and turned into AgentResult(status=FAIL),
never an accidental PASS.
"""

from __future__ import annotations

import ast
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext

ROOT = Path(__file__).resolve().parents[2]

_SECRET_TYPES = {"secrets_exposure"}
_SECRET_CWES = {"CWE-798", "CWE-259"}
_ACCESS_TYPES = {"broken_access_control"}
_ACCESS_CWES = {"CWE-639", "CWE-862"}

_ASSIGN_RE = re.compile(
    r'^(?P<indent>\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<q>[\'"])(?P<val>.*?)(?P=q)\s*$'
)
_RESOURCE_NAME_HINTS = ("task", "item", "resource", "obj", "record", "entity")


@dataclass
class _PatchOutcome:
    finding_id: str
    location: str
    fixed: bool
    detail: str


class FixAdapter(BaseAgent):
    """Real Fix agent -- patches the finding(s) Security actually reported."""

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        try:
            return self._run(context, start)
        except Exception as exc:  # noqa: BLE001 - must never crash the pipeline
            return AgentResult(
                agent="fix_agent",
                status=AgentStatus.FAIL,
                summary=f"Fix agent crashed: {exc}",
                data={"outcomes": []},
                duration_seconds=round(time.time() - start, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def _run(self, context: ProjectContext, start: float) -> AgentResult:
        sec = (context.last_security_result or {}).get("data", {})
        findings = sec.get("findings", [])

        if not findings:
            return AgentResult(
                agent="fix_agent",
                status=AgentStatus.FAIL,
                summary="No security findings on context to fix (last_security_result is empty).",
                data={"outcomes": []},
                duration_seconds=round(time.time() - start, 3),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        scan_path = sec.get("scan_path")
        outcomes_by_id = self._patch_all(findings, scan_path)
        outcomes = [outcomes_by_id[f.get("id", "SEC-000")] for f in findings]
        fixed = [o for o in outcomes if o.fixed]

        summary = "; ".join(
            f"{'fixed' if o.fixed else 'SKIPPED'} {o.finding_id} @ {o.location}: {o.detail}"
            for o in outcomes
        )
        return AgentResult(
            agent="fix_agent",
            status=AgentStatus.PASS if fixed else AgentStatus.FAIL,
            summary=summary or "No findings could be patched.",
            data={
                "patched_files": sorted({o.location.rsplit(":", 1)[0] for o in fixed}),
                "outcomes": [asdict(o) for o in outcomes],
            },
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # -- resolve, order, dispatch -----------------------------------------

    def _patch_all(self, findings: list[dict[str, Any]], scan_path: str | None) -> dict[str, _PatchOutcome]:
        resolved: list[tuple[dict[str, Any], Path, int]] = []
        outcomes: dict[str, _PatchOutcome] = {}

        for finding in findings:
            finding_id = finding.get("id", "SEC-000")
            location = finding.get("location", "?:0")
            file_part, sep, line_part = location.rpartition(":")
            if not sep:
                outcomes[finding_id] = _PatchOutcome(finding_id, location, False, "could not parse file:line from location")
                continue
            try:
                line_no = int(line_part)
            except ValueError:
                outcomes[finding_id] = _PatchOutcome(finding_id, location, False, "could not parse file:line from location")
                continue

            target = self._resolve_target(file_part, scan_path)
            if target is None:
                outcomes[finding_id] = _PatchOutcome(finding_id, location, False, f"{file_part} does not exist under the workspace")
                continue

            resolved.append((finding, target, line_no))

        for finding, target, line_no in sorted(resolved, key=lambda t: t[2], reverse=True):
            finding_id = finding.get("id", "SEC-000")
            location = finding.get("location", "?:0")
            ftype = (finding.get("type") or "").lower()
            cwe = (finding.get("cwe") or "").upper()

            if ftype in _SECRET_TYPES or cwe in _SECRET_CWES:
                outcomes[finding_id] = self._patch_secret(finding_id, location, target, line_no)
            elif ftype in _ACCESS_TYPES or cwe in _ACCESS_CWES:
                outcomes[finding_id] = self._patch_access_control(finding_id, location, target, line_no)
            else:
                outcomes[finding_id] = _PatchOutcome(finding_id, location, False, f"no patcher for type={ftype or '?'} cwe={cwe or '?'}")

        return outcomes

    @staticmethod
    def _resolve_target(file_part: str, scan_path: str | None) -> Path | None:
        candidates = [ROOT / file_part]
        if scan_path:
            scan_dir = (ROOT / scan_path).parent if not (ROOT / scan_path).is_dir() else ROOT / scan_path
            candidates.append(scan_dir / file_part)

        for candidate in candidates:
            try:
                resolved = candidate.resolve()
                resolved.relative_to(ROOT)
            except (OSError, ValueError):
                continue
            if resolved.is_file():
                return resolved

        basename = Path(file_part).name
        matches = [p for p in ROOT.rglob(basename) if p.is_file() and "__pycache__" not in p.parts]
        if len(matches) == 1:
            return matches[0].resolve()
        return None

    @staticmethod
    def _patch_secret(finding_id: str, location: str, target: Path, line_no: int) -> _PatchOutcome:
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return _PatchOutcome(finding_id, location, False, f"could not read file: {exc}")

        if not (1 <= line_no <= len(lines)):
            return _PatchOutcome(finding_id, location, False, f"line {line_no} out of range")

        m = _ASSIGN_RE.match(lines[line_no - 1])
        if not m:
            return _PatchOutcome(finding_id, location, False, "line is not a simple NAME = \"literal\" assignment")
        var_name = m.group("name")

        from security.fix_agent import fix_hardcoded_secret

        result = fix_hardcoded_secret({"file": str(target), "line": line_no, "var_name": var_name})
        status = result.get("status")
        message = result.get("message", "")
        if status == "FIXED":
            return _PatchOutcome(finding_id, location, True, message)
        return _PatchOutcome(finding_id, location, False, message or f"fix_agent returned {status}")

    def _patch_access_control(self, finding_id: str, location: str, target: Path, line_no: int) -> _PatchOutcome:
        try:
            source = target.read_text(encoding="utf-8")
        except OSError as exc:
            return _PatchOutcome(finding_id, location, False, f"could not read file: {exc}")

        try:
            tree = ast.parse(source, filename=str(target))
        except SyntaxError as exc:
            return _PatchOutcome(finding_id, location, False, f"file does not parse: {exc}")

        func = self._enclosing_function(tree, line_no)
        if func is None:
            return _PatchOutcome(finding_id, location, False, "could not locate the enclosing route function")

        if self._has_ownership_check(func):
            return _PatchOutcome(finding_id, location, True, f"{func.name}() already has an ownership/403 check")

        resource_var, user_expr, anchor_line = self._locate_insertion_point(func)
        if resource_var is None or user_expr is None:
            return _PatchOutcome(
                finding_id, location, False,
                "could not infer the resource/current-user variable names to build a safe check",
            )

        lines = source.splitlines(keepends=True)
        indent_match = re.match(r"^(\s*)", lines[anchor_line - 1])
        indent = indent_match.group(1) if indent_match else "    "
        check = (
            f"{indent}if {resource_var}.owner_id != {user_expr}.id:\n"
            f"{indent}    raise HTTPException(status_code=403)\n"
        )
        lines.insert(anchor_line, check)

        if "HTTPException" not in source:
            lines = self._insert_import(lines, "from fastapi import HTTPException\n")

        try:
            target.write_text("".join(lines), encoding="utf-8")
        except OSError as exc:
            return _PatchOutcome(finding_id, location, False, f"could not write file: {exc}")

        return _PatchOutcome(
            finding_id, location, True,
            f"inserted ownership check ({resource_var}.owner_id != {user_expr}.id) into {func.name}() in {target.name}",
        )

    @staticmethod
    def _insert_import(lines: list[str], import_line: str) -> list[str]:
        i = 0
        if i < len(lines) and lines[i].lstrip().startswith(('"""', "'''")):
            quote = lines[i].lstrip()[:3]
            stripped = lines[i].strip()
            if stripped.endswith(quote) and len(stripped) > 3:
                i += 1
            else:
                i += 1
                while i < len(lines) and quote not in lines[i]:
                    i += 1
                i += 1
        while i < len(lines) and lines[i].lstrip().startswith("from __future__"):
            i += 1
        return lines[:i] + [import_line] + lines[i:]

    @staticmethod
    def _enclosing_function(tree: ast.AST, line_no: int):
        best = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorator_starts = [d.lineno for d in node.decorator_list]
                start = min([node.lineno, *decorator_starts]) if decorator_starts else node.lineno
                end = getattr(node, "end_lineno", None) or node.lineno
                if start <= line_no <= end and (best is None or node.lineno > best.lineno):
                    best = node
        return best

    @staticmethod
    def _has_ownership_check(func) -> bool:
        dump = ast.dump(func)
        has_owner_ref = "owner_id" in dump or "owner" in dump or "user_id" in dump
        has_current_user = "current_user" in dump
        has_403 = "403" in dump
        if (has_owner_ref and has_current_user) or has_403:
            return True
        for node in ast.walk(func):
            if isinstance(node, ast.Compare):
                combined = ast.dump(node.left) + "".join(ast.dump(c) for c in node.comparators)
                if "owner" in combined or "user_id" in combined:
                    return True
        return False

    @staticmethod
    def _locate_insertion_point(func) -> tuple[str | None, str | None, int | None]:
        resource_var = resource_line = None
        user_expr = user_line = None

        for node in func.body:
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
                continue
            name = node.targets[0].id
            end_line = getattr(node, "end_lineno", node.lineno)

            if resource_var is None and name.lower() in _RESOURCE_NAME_HINTS:
                resource_var = name
                resource_line = end_line

            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and "current_user" in node.value.func.id.lower()
            ):
                user_expr = name
                user_line = end_line

        if resource_var is None or user_expr is None:
            return None, None, None
        return resource_var, user_expr, max(resource_line, user_line)
