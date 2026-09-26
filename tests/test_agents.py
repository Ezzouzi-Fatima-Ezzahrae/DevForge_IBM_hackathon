from agents.plan_agent import run
from orchestrator.contracts import ProjectContext
from orchestrator.gates import evaluate_plan_gate


def test_plan_agent_output_passes_gate():
    result = run(
        {"idea": "task-management SaaS for small teams"}
    )

    context = ProjectContext(
        project_id="proj_task_management",
        idea="task-management SaaS for small teams",
        created_at="2026-09-26T00:00:00Z",
    )

    gate = evaluate_plan_gate(result, context)

    assert gate.verdict.value == "PASS"
