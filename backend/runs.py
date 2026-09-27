from threading import Thread

from orchestrator.approval_broker import make_approval_fn
from orchestrator.runner import run_pipeline


_running: set[str] = set()


def start_run(project_id: str, idea: str) -> bool:
    """Start a project pipeline in a background thread."""

    if project_id in _running:
        return False

    _running.add(project_id)

    def run() -> None:
        try:
            run_pipeline(
                idea,
                project_id=project_id,
                approval_fn=make_approval_fn(project_id),
            )
        finally:
            _running.discard(project_id)

    Thread(target=run, daemon=True).start()
    return True


def is_running(project_id: str) -> bool:
    return project_id in _running