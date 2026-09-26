"""
security/security_agent.py
Security Red-Team Agent — DevForge pipeline.

Responsibilities:
    1. Receive a code snapshot (files[], dependencies[]).
    2. Run the security scanners (Bandit + custom authorization checker).
    3. Evaluate findings through the security gate.
    4. Return an AgentResult with verdict PASS or BLOCKED.
    5. Never modify project.status — that is the orchestrator's job.

Two operating modes:

    REAL mode (demo_mode=False, controlled by DEMO_MODE env var):
        Runs actual Bandit + AST-based authorization checker against
        the provided files / scan path.

    DEMO mode (demo_mode=True):
        Returns pre-recorded fixtures in a deterministic sequence:
            call 1 → security_finding_HIGH.json  (BLOCKED)
            call 2 → security_pass.json           (PASS)
        This makes the demo reproducible without live LLM or scanner calls.

    IMPORTANT: Demo mode is an alternative delivery path, not a fake.
    The real scanning code is fully implemented and reachable via
    SecurityAgent(demo_mode=False).

Security rules applied here:
    - Paths from caller input are validated before use.
    - LLM/AI output (if integrated) must be validated before storage.
    - Scanner errors are surfaced as status="ERROR", never silently as PASS.
    - No secrets are hardcoded.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory.schemas import GateResult, SecurityFinding
from security.gate import evaluate_security_gate
from security.scanner import ScannerError, scan

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
_FIXTURE_BLOCKED = _FIXTURE_DIR / "security_finding_HIGH.json"
_FIXTURE_PASS    = _FIXTURE_DIR / "security_pass.json"


# ---------------------------------------------------------------------------
# Security Agent
# ---------------------------------------------------------------------------

class SecurityAgent:
    """
    Stateless (per-milestone) security analysis agent.

    Args:
        demo_mode:  When True, replay fixtures for deterministic demo.
                    Defaults to the DEMO_MODE environment variable ("1" = True).
        workspace_root:
                    Restrict scanner path traversal to this directory.
                    Defaults to the project root (two levels up from this file).
    """

    def __init__(
        self,
        demo_mode: Optional[bool] = None,
        workspace_root: Optional[str] = None,
    ) -> None:
        if demo_mode is None:
            demo_mode = os.environ.get("DEMO_MODE", "0") == "1"
        self.demo_mode = demo_mode
        self.workspace_root = workspace_root or str(
            Path(__file__).parent.parent.resolve()
        )
        # Per-milestone call counter — reset via reset_call_count()
        self._call_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the security agent for one milestone scan.

        Args:
            input_data: Dict containing at minimum:
                {
                    "files": ["backend/routers/tasks.py", ...],
                    "dependencies": ["fastapi==0.111.0", ...],
                    "milestone_id": "ms_001",        # optional, defaults to "ms_unknown"
                    "scan_path": "backend/"          # optional override for scanner path
                }

        Returns:
            AgentResult-compatible dict:
            {
                "agent": "security_agent",
                "milestone_id": "...",
                "status": "PASS" | "BLOCKED" | "ERROR",
                "summary": "...",
                "payload": {
                    "verdict": "PASS" | "BLOCKED",
                    "findings": [...],
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    ...
                },
                "duration_seconds": 4.2,
                "timestamp": "..."
            }
        """
        start_time = time.monotonic()
        milestone_id = input_data.get("milestone_id", "ms_unknown")

        logger.info(
            "Security scan started | milestone=%s demo_mode=%s call=%d",
            milestone_id,
            self.demo_mode,
            self._call_count + 1,
        )

        if self.demo_mode:
            result = self._run_demo(input_data, milestone_id)
        else:
            result = self._run_real(input_data, milestone_id)

        duration = round(time.monotonic() - start_time, 2)
        result["duration_seconds"] = duration
        result["timestamp"] = datetime.now(timezone.utc).isoformat()

        self._call_count += 1

        logger.info(
            "Security scan finished | milestone=%s status=%s duration=%.2fs",
            milestone_id,
            result["status"],
            duration,
        )

        return result

    def reset_call_count(self) -> None:
        """
        Reset the per-milestone call counter.
        The orchestrator must call this when starting a new milestone so that
        the demo fixture sequence restarts from call 1.
        """
        self._call_count = 0
        logger.debug("SecurityAgent call counter reset")

    # ------------------------------------------------------------------
    # Demo mode (deterministic fixture replay)
    # ------------------------------------------------------------------

    def _run_demo(
        self,
        input_data: Dict[str, Any],
        milestone_id: str,
    ) -> Dict[str, Any]:
        """Return pre-recorded fixture based on call count (0-indexed)."""
        # Call 0 → BLOCKED (planted vulnerability found)
        # Call 1+ → PASS (after fix)
        fixture_path = _FIXTURE_BLOCKED if self._call_count == 0 else _FIXTURE_PASS

        if not fixture_path.exists():
            logger.error("Demo fixture not found: %s", fixture_path)
            return self._error_result(
                milestone_id,
                f"Demo fixture missing: {fixture_path.name}",
            )

        try:
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load demo fixture %s: %s", fixture_path, exc)
            return self._error_result(milestone_id, f"Fixture load error: {exc}")

        # Stamp the current milestone_id into the fixture result
        data["milestone_id"] = milestone_id
        return data

    # ------------------------------------------------------------------
    # Real mode (live scanning)
    # ------------------------------------------------------------------

    def _run_real(
        self,
        input_data: Dict[str, Any],
        milestone_id: str,
    ) -> Dict[str, Any]:
        """Run actual scanners and evaluate the security gate."""
        # Determine what to scan
        scan_path = self._resolve_scan_path(input_data)
        if scan_path is None:
            return self._error_result(
                milestone_id,
                "No scannable path found in input (provide 'scan_path' or 'files')",
            )

        # Run scanners
        try:
            findings: List[SecurityFinding] = scan(
                path=scan_path,
                workspace_root=self.workspace_root,
                use_bandit=True,
                use_auth_checker=True,
            )
        except FileNotFoundError as exc:
            return self._error_result(milestone_id, f"Scan path error: {exc}")
        except ValueError as exc:
            return self._error_result(milestone_id, f"Path validation error: {exc}")
        except ScannerError as exc:
            # Scanner failed — must NOT return PASS
            logger.error("Scanner error: %s", exc)
            return self._error_result(milestone_id, str(exc))

        # Evaluate gate
        gate_result: GateResult = evaluate_security_gate(findings, milestone_id)

        # Build summary
        d = gate_result.details
        summary = self._build_summary(gate_result.verdict, d, findings)

        logger.info(
            "Security gate result | milestone=%s verdict=%s critical=%d high=%d medium=%d",
            milestone_id,
            gate_result.verdict,
            d.get("critical", 0),
            d.get("high", 0),
            d.get("medium", 0),
        )

        return {
            "agent": "security_agent",
            "milestone_id": milestone_id,
            "status": gate_result.verdict,   # "PASS" or "BLOCKED"
            "summary": summary,
            "payload": {
                "verdict": gate_result.verdict,
                "findings": [f.model_dump() for f in findings],
                "critical_count": d.get("critical", 0),
                "high_count":     d.get("high", 0),
                "medium_count":   d.get("medium", 0),
                "low_count":      d.get("low", 0),
                "info_count":     d.get("info", 0),
                "total_open":     d.get("total_open", 0),
                "scan_path":      scan_path,
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_scan_path(self, input_data: Dict[str, Any]) -> Optional[str]:
        """
        Determine the best path to scan from the agent input.

        Priority:
            1. Explicit "scan_path" key in input.
            2. Parent directory of the first file in "files".
            3. None — caller must handle this.
        """
        if "scan_path" in input_data and input_data["scan_path"]:
            return str(input_data["scan_path"])

        files: List[str] = input_data.get("files", [])
        if files:
            # Use the parent directory of the first file so the scanner
            # gets full context, not just one file.
            parent = Path(files[0]).parent
            if parent.exists():
                return str(parent)
            # Fallback: try each file individually
            for f in files:
                if Path(f).exists():
                    return str(Path(f).parent)

        return None

    @staticmethod
    def _build_summary(
        verdict: str,
        details: Dict[str, Any],
        findings: List[SecurityFinding],
    ) -> str:
        critical = details.get("critical", 0)
        high     = details.get("high", 0)
        medium   = details.get("medium", 0)
        total    = details.get("total_findings", len(findings))

        if verdict == "PASS":
            if medium > 0:
                return (
                    f"Security gate PASS. {total} finding(s) scanned. "
                    f"0 critical, 0 high. {medium} medium (informational)."
                )
            return f"Security gate PASS. No critical or high severity findings."

        # BLOCKED
        blocking = [
            f for f in findings
            if f.status == "OPEN" and f.severity in ("CRITICAL", "HIGH")
        ]
        parts = []
        if critical > 0:
            parts.append(f"{critical} CRITICAL")
        if high > 0:
            parts.append(f"{high} HIGH")
        desc = ", ".join(parts)

        if blocking:
            first = blocking[0]
            return (
                f"Security gate BLOCKED. {desc} finding(s) detected. "
                f"First: [{first.cwe}] {first.description} "
                f"({first.file}:{first.line})"
            )
        return f"Security gate BLOCKED. {desc} finding(s) detected."

    @staticmethod
    def _error_result(milestone_id: str, message: str) -> Dict[str, Any]:
        """
        Build an ERROR result.

        IMPORTANT: An ERROR result must never be treated as PASS.
        The orchestrator should route this to HUMAN_REVIEW or raise an alert.
        """
        logger.error("Security agent error | milestone=%s msg=%s", milestone_id, message)
        return {
            "agent": "security_agent",
            "milestone_id": milestone_id,
            "status": "ERROR",
            "summary": f"Security scan failed: {message}",
            "payload": {
                "verdict": "ERROR",
                "findings": [],
                "error": message,
            },
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# Orchestrator and runner.py use: from security.security_agent import run
# ---------------------------------------------------------------------------

_agent = SecurityAgent()


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level entry point compatible with the runner's agent dispatch.
    Usage: result = security.security_agent.run({"files": [...], "milestone_id": "ms_001"})
    """
    return _agent.run(input_data)


def reset_demo_counter() -> None:
    """Reset the demo fixture counter. Call this when starting a new milestone."""
    _agent.reset_call_count()
