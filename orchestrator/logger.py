"""
orchestrator/logger.py
Structured JSON-line logger for all orchestrator events.
Writes to logs/orchestrator.jsonl (path from config).
Also exposed as get_logger() for use in runner.py.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OrchestratorLogger:
    """
    Appends one JSON object per line to the log file.
    Each event has at minimum: ts, event, project_id.
    """

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, payload: dict) -> None:
        payload.setdefault("ts", datetime.now(timezone.utc).isoformat())
        line = json.dumps(payload, default=str)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # Also echo a one-liner to stdout for the CLI
        print(f"  [{payload.get('event','LOG')}] {payload.get('msg', '')}", flush=True)

    def transition(self, project_id: str, from_state: str, to_state: str) -> None:
        self._write({
            "event": "STATE_TRANSITION",
            "project_id": project_id,
            "from": from_state,
            "to": to_state,
            "msg": f"{from_state} → {to_state}",
        })

    def agent_start(self, project_id: str, agent: str, stage: str) -> None:
        self._write({
            "event": "AGENT_START",
            "project_id": project_id,
            "agent": agent,
            "stage": stage,
            "msg": f"Running {agent} for stage '{stage}'",
        })

    def agent_done(
        self,
        project_id: str,
        agent: str,
        stage: str,
        status: str,
        duration: float,
        summary: str,
    ) -> None:
        self._write({
            "event": "AGENT_DONE",
            "project_id": project_id,
            "agent": agent,
            "stage": stage,
            "status": status,
            "duration_seconds": duration,
            "summary": summary,
            "msg": f"{agent} → {status} ({duration:.2f}s): {summary}",
        })

    def gate(
        self,
        project_id: str,
        gate: str,
        verdict: str,
        reason: str,
        retry: int = 0,
    ) -> None:
        self._write({
            "event": "GATE",
            "project_id": project_id,
            "gate": gate,
            "verdict": verdict,
            "retry": retry,
            "reason": reason,
            "msg": f"GATE {gate.upper()} → {verdict} (retry={retry}): {reason}",
        })

    def retry(self, project_id: str, stage: str, attempt: int, max_retries: int) -> None:
        self._write({
            "event": "RETRY",
            "project_id": project_id,
            "stage": stage,
            "attempt": attempt,
            "max": max_retries,
            "msg": f"Retry {attempt}/{max_retries} for stage '{stage}'",
        })

    def escalation(self, project_id: str, stage: str, reason: str) -> None:
        self._write({
            "event": "ESCALATION",
            "project_id": project_id,
            "stage": stage,
            "reason": reason,
            "msg": f"⚠ ESCALATION stage='{stage}': {reason}",
        })

    def human_approval(self, project_id: str, gate: str, approved: bool) -> None:
        self._write({
            "event": "HUMAN_APPROVAL",
            "project_id": project_id,
            "gate": gate,
            "approved": approved,
            "msg": f"Human {'approved' if approved else 'rejected'} gate='{gate}'",
        })

    def info(self, project_id: str, msg: str, **extra: Any) -> None:
        self._write({"event": "INFO", "project_id": project_id, "msg": msg, **extra})

    def error(self, project_id: str, msg: str, **extra: Any) -> None:
        self._write({"event": "ERROR", "project_id": project_id, "msg": msg, **extra})


# ─── Module-level singleton ────────────────────────────────────────────────────

_logger: OrchestratorLogger | None = None


def get_logger(log_path: str | Path | None = None) -> OrchestratorLogger:
    """Return the singleton logger, creating it on first call."""
    global _logger
    if _logger is None:
        if log_path is None:
            import json as _json
            from pathlib import Path as _Path
            cfg_path = _Path(__file__).parent.parent / "config" / "orchestrator_config.json"
            with open(cfg_path) as f:
                cfg = _json.load(f)
            log_path = cfg.get("log_file", "logs/orchestrator.jsonl")
        _logger = OrchestratorLogger(log_path)
    return _logger
