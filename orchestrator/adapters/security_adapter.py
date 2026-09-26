"""
orchestrator/adapters/security_adapter.py
Connects Haytam's security agent (security/security_agent.py) to the orchestrator.

The security package has its own result format (dict with "payload", severities in
capitals). This adapter converts it to the shared AgentResult contract:
    data = {"verdict": "PASS" | "BLOCKED", "counts": {...}, "findings": [SecurityFinding]}
so orchestrator/gates.py can evaluate it.

Never raises: any problem becomes AgentResult(status=ERROR), which the gate treats as BLOCKED.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.agents_base import BaseAgent
from orchestrator.contracts import AgentResult, AgentStatus, ProjectContext

ROOT = Path(__file__).resolve().parents[2]

# Default file the security agent scans (the shared demo app).
DEFAULT_SCAN_PATH = "backend/demo_bug.py"

_TYPE_MAP = {
    "broken_access_control": "broken_access_control",
    "injection": "injection",
    "secrets_exposure": "secrets_exposure",
    "xss": "xss",
    "csrf": "csrf",
    "vulnerable_dependency": "vulnerable_dependency",
}
_BANDIT_SECRET_IDS = {"b105", "b106", "b107"}


def _finding_type(category: str) -> str:
    category = (category or "").lower()
    if category in _TYPE_MAP:
        return _TYPE_MAP[category]
    if category in _BANDIT_SECRET_IDS:
        return "secrets_exposure"
    return "misconfiguration"


class SecurityAdapter(BaseAgent):
    """Runs the real security agent for the orchestrator stage "security"."""

    def __init__(self, scan_path: str | None = None) -> None:
        self.scan_path = scan_path or os.environ.get("DEVFORGE_SECURITY_SCAN_PATH", DEFAULT_SCAN_PATH)

    def reset(self) -> None:  # interface used by the runner between milestones
        pass

    def run(self, context: ProjectContext) -> AgentResult:
        start = time.time()
        milestone_id = "ms_unknown"
        if context.milestones:
            milestone_id = context.milestones[context.current_milestone_index].id
        try:
            # Imported here so a problem in the security package cannot break the orchestrator at import time.
            from security.security_agent import SecurityAgent

            agent = SecurityAgent(demo_mode=False, workspace_root=str(ROOT))
            raw = agent.run({"scan_path": str(ROOT / self.scan_path), "milestone_id": milestone_id})
        except Exception as exc:  # noqa: BLE001 - must never crash the pipeline
            return self._error(f"Security agent crashed: {exc}", start)

        status = raw.get("status")
        payload = raw.get("payload", {})
        if status == "ERROR" or payload.get("verdict") == "ERROR":
            return self._error(raw.get("summary", "Security scan failed"), start)

        findings = []
        for f in payload.get("findings", []):
            if f.get("status", "OPEN") != "OPEN":
                continue
            findings.append(
                {
                    "id": f.get("id", "SEC-000"),
                    "severity": str(f.get("severity", "low")).lower(),
                    "type": _finding_type(f.get("category", "")),
                    "location": f"{f.get('file', '?')}:{f.get('line', 0)}",
                    "description": f.get("description", ""),
                    "recommended_fix": f.get("recommendation") or "See CWE " + str(f.get("cwe", "")),
                    "cwe": f.get("cwe", ""),
                }
            )

        counts = {
            "critical": payload.get("critical_count", 0),
            "high": payload.get("high_count", 0),
            "medium": payload.get("medium_count", 0),
            "low": payload.get("low_count", 0),
        }
        verdict = "BLOCKED" if status == "BLOCKED" else "PASS"
        return AgentResult(
            agent="security_agent",
            status=AgentStatus.FAIL if verdict == "BLOCKED" else AgentStatus.PASS,
            summary=raw.get("summary", ""),
            data={"verdict": verdict, "counts": counts, "findings": findings, "scan_path": self.scan_path},
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _error(message: str, start: float) -> AgentResult:
        return AgentResult(
            agent="security_agent",
            status=AgentStatus.ERROR,
            summary=message,
            data={"verdict": "BLOCKED", "counts": {}, "findings": [], "error": message},
            duration_seconds=round(time.time() - start, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
