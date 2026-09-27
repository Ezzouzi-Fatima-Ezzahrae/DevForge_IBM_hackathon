from fastapi import APIRouter

from memory.memory_agent import query, query_gate_results
from memory.metrics import get_summary

router = APIRouter(prefix="/projects", tags=["insights"])


def _build_impact_text(summary: dict) -> str:
    """Wording honnête : uniquement ce que get_summary a mesuré, rien d'inventé."""
    security_findings = summary.get("security_findings_count", 0)
    retries = summary.get("retry_count", 0)
    human_interventions = summary.get("human_interventions", 0)
    debugging_time = summary.get("debugging_time_seconds", 0)

    if not security_findings and not retries and not debugging_time and not human_interventions:
        return "Aucune activité mesurée pour ce projet pour l'instant."

    parts = []
    if debugging_time:
        parts.append("un cycle de correction automatique par l'agent de debug a eu lieu")
    if security_findings:
        parts.append(f"{security_findings} faille(s) de sécurité détectée(s)")
    if retries:
        parts.append(f"{retries} boucle(s) de retry utilisée(s)")
    if human_interventions:
        parts.append(f"{human_interventions} intervention(s) humaine(s)")
    return "Sur ce run : " + ", ".join(parts) + "."


@router.get("/{project_id}/metrics")
def get_project_metrics(project_id: str):
    summary = get_summary(project_id)
    return {"summary": summary, "impact_text": _build_impact_text(summary)}


@router.get("/{project_id}/decisions")
def get_project_decisions(project_id: str):
    return query(project_id)


@router.get("/{project_id}/gates")
def get_project_gates(project_id: str):
    return query_gate_results(project_id)


@router.get("/{project_id}/tests")
def get_project_tests(project_id: str):
    gates = query_gate_results(project_id)
    return [g for g in gates if g.get("gate") == "tests"]


@router.get("/{project_id}/security")
def get_project_security(project_id: str):
    gates = query_gate_results(project_id)
    return [g for g in gates if g.get("gate") == "security"]
