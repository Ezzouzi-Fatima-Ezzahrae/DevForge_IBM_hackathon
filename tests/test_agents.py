from copy import deepcopy

from agents.plan_agent import run
from orchestrator.contracts import ProjectContext
from orchestrator.gates import evaluate_plan_gate


def make_context():
    return ProjectContext(
        project_id="proj_task_management",
        idea="task-management SaaS for small teams",
        created_at="2026-09-26T00:00:00Z",
    )


def test_plan_agent_output_passes_gate():
    result = run(
        {
            "project_id": "proj_task_management",
            "idea": "task-management SaaS for small teams",
        }
    )

    context = make_context()
    gate = evaluate_plan_gate(result, context)

    assert gate.verdict.value == "PASS"


def test_plan_with_fewer_than_5_stories_fails_gate():
    result = run(
        {
            "project_id": "proj_task_management",
            "idea": "task-management SaaS for small teams",
        }
    )

    result = deepcopy(result)
    result.data["requirements"] = result.data["requirements"][:4]

    context = make_context()
    gate = evaluate_plan_gate(result, context)

    assert gate.verdict.value == "FAIL"


def test_plan_without_adr_fails_gate():
    result = run(
        {
            "project_id": "proj_task_management",
            "idea": "task-management SaaS for small teams",
        }
    )

    result = deepcopy(result)
    result.data["architecture"]["adr"] = []

    context = make_context()
    gate = evaluate_plan_gate(result, context)

    assert gate.verdict.value == "FAIL"
    
def test_plan_decisions_use_context_project_id():
    result = run(
        {
            "project_id": "my_project_123",
            "idea": "another SaaS idea",
        }
    )

    for decision in result.data["decisions"]:
        assert decision["project_id"] == "my_project_123"