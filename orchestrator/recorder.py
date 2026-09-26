"""
orchestrator/recorder.py
Records what happens during a run in Safa's memory and metrics modules.

- metrics.record_event(...)       time per stage, test counts, retries, security
                                  findings, real human approvals
- memory_agent.store(...)         decisions produced by the plan agent
- memory_agent.store_gate_result  every quality gate result

Rules:
- Never raises. A problem in memory or metrics is logged and the pipeline continues.
- Can be switched off: config "memory": {"enabled": false} or environment
  variable DEVFORGE_MEMORY=off.
- Live events carry the run id "live-<project_id>". Do not run memory/log_ingest.py
  for the same project, or the numbers would be counted twice.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from orchestrator.contracts import AgentResult, GateResult
from orchestrator.logger import get_logger

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "orchestrator_config.json"

# pipeline stage -> metric event type (seconds)
_TIME_EVENT = {
    "plan": "planning_time",
    "build": "implementation_time",
    "test": "testing_time",
    "debug": "debugging_time",
    "fix": "debugging_time",
}


def _memory_enabled() -> bool:
    env = os.environ.get("DEVFORGE_MEMORY", "").strip().lower()
    if env in ("off", "0", "false", "no"):
        return False
    if env in ("on", "1", "true", "yes"):
        return True
    try:
        cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return bool(cfg.get("memory", {}).get("enabled", True))
    except Exception:  # noqa: BLE001
        return True


class Recorder:
    def __init__(self, project_id: str, enabled: bool | None = None) -> None:
        self.project_id = project_id
        self.run_id = f"live-{project_id}"
        self.enabled = _memory_enabled() if enabled is None else enabled

    # -- internals ---------------------------------------------------------

    def _safe(self, what: str, fn, *args: Any, **kwargs: Any) -> None:
        if not self.enabled:
            return
        try:
            fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - memory must never stop the pipeline
            try:
                get_logger().error(self.project_id, f"memory: {what} failed: {exc}")
            except Exception:  # noqa: BLE001
                pass

    def _metric(self, event_type: str, value: float) -> None:
        from memory import metrics

        self._safe(f"metric {event_type}", metrics.record_event, self.project_id, event_type, value, run_id=self.run_id)

    # -- events ------------------------------------------------------------

    def agent_done(self, stage: str, result: AgentResult) -> None:
        """Called after every agent run."""
        if not self.enabled:
            return
        event = _TIME_EVENT.get(stage)
        if event:
            self._metric(event, result.duration_seconds)
        if stage == "test":
            total = result.data.get("total", 0)
            passed = result.data.get("passed", 0)
            if total:
                self._metric("test_passed", passed)
                self._metric("test_failed", total - passed)
        elif stage == "security":
            findings = [f for f in result.data.get("findings", [])]
            if findings:
                self._metric("security_finding", len(findings))

    def retry(self, stage: str) -> None:
        self._metric("retry", 1)

    def approval(self, approved: bool, auto: bool) -> None:
        """Only a real (non-automatic) human decision counts as an intervention."""
        if not auto:
            self._metric("human_intervention", 1)

    def gate(self, gate_result: GateResult) -> None:
        from memory import memory_agent

        self._safe("gate result", memory_agent.store_gate_result, gate_result.model_dump(mode="json"))

    def decisions(self, plan_result: AgentResult) -> None:
        """Store the decisions of a plan result (once per passing plan)."""
        from memory import memory_agent

        for raw in plan_result.data.get("decisions", []) or []:
            decision = dict(raw)
            decision["project_id"] = self.project_id  # always the running project
            decision.setdefault("source", plan_result.agent)
            if not decision.get("alternatives"):
                continue
            decision.pop("id", None)  # let memory assign a fresh id
            self._safe("decision", memory_agent.store, decision)
