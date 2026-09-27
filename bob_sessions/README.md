# Bob sessions: evidence of how IBM Bob was used

Every screenshot in this folder is an **IBM Bob IDE task screenshot** (Tasks tab, chat panel, task header with the token and Bobcoin figures), saved as PNG with the naming rule of the hackathon guide: `devforge_taskNN_<owner>_<description>.png`. Each teammate also wrote a session file (`*_session.md`) that says what was asked, what Bob produced and what was adapted afterwards.

## Index

| # | Screenshot | Owner | Bob task | Mode and what it shows |
|---|---|---|---|---|
| 01 | `devforge_task01_leader_architecture_review.png` | Leader | Final MVP architecture | Plan mode: architecture review, task list 9/9, follow-up prompts |
| 02 | `devforge_task02_leader_project_structure.png` | Leader | Repository skeleton | Agent mode: commands and files created (11 files) |
| 03 | `devforge_task03_leader_contracts_and_models.png` | Leader | Shared data contracts | Agent mode: contracts doc, Pydantic models, tests run |
| 04 | `devforge_task04_leader_orchestrator_consumption_summary.png` | Leader | Orchestrator skeleton | **Task consumption summary**: context 239.7k / 270.0k tokens, 40.23 Bobcoins |
| 05 | `devforge_task05_leader_orchestrator_todo_list_and_demo.png` | Leader | Orchestrator skeleton | Bob task list (13/21) next to the finished demo running |
| 06 | `devforge_task06_leader_orchestrator_result_released.png` | Leader | Orchestrator skeleton | Bob task next to the final result card: 17/20 to 20/20, BLOCKED to PASS, RELEASED |
| 07 | `devforge_task07_leader_orchestrator_full_run.png` | Leader | Orchestrator skeleton | Same run, full terminal view |
| 08 | `devforge_task08_fati_plan_gate_check.png` | Fati | Plan agent | Plan mode: plan checked against the plan gate |
| 09 | `devforge_task09_fati_plan_generation.png` | Fati | Plan agent | Plan mode: requirements with acceptance criteria |
| 10 | `devforge_task10_fati_plan_review.png` | Fati | Plan agent | Review of the generated plan |
| 11 | `devforge_task11_fati_plan_agent_integration.png` | Fati | Plan agent | Alignment with the `AgentResult` contract |
| 12 | `devforge_task12_fati_plan_agent_testing.png` | Fati | Plan agent | Decisions in the memory format, test run |
| 13 | `devforge_task13_manar_testing_agent.png` | Manar | Testing agent | Agent mode: testing agent and 17/20 fixture |
| 14 | `devforge_task14_manar_debug_agent.png` | Manar | Debug agent | Agent mode: debug agent files, ownership fix, result 20/20 |
| 15 | `devforge_task15_safa_decision_memory.png` | Safa | Decision memory | Agent mode: `memory_agent.py` build |
| 16 | `devforge_task16_safa_metrics.png` | Safa | Metrics | `metrics.py` function-by-function |
| 17 | `devforge_task17_safa_impact_summary.png` | Safa | Impact summary | `get_impact_summary` with a data-flow diagram |
| 18 | `devforge_task18_safa_type_fix.png` | Safa | Type fix | Fixing a parameter type flagged by the checker |
| 19 | `devforge_task19_safa_editor_config.png` | Safa | Editor config | Type-checker configuration fix |
| 20 | `devforge_task20_safa_bob_code_review.png` | Safa | Code review | Bob reviews the four memory APIs |
| 21 | `devforge_task21_safa_context_injection.png` | Safa | Context injection | Top-5 decisions as a prompt prefix, 19/19 tasks |

Session files: `leader_orchestrator_session.md`, `fati_plan_agent_session.md`, `manar_tester_session.md`, `manar_debugger_session.md`, `safae_memory_session.md`, `haytam_security_session.md`.

## Bob features used

- **Plan mode:** the architecture (Leader) and the plan agent's requirements and decisions (Fati).
- **Agent mode:** contracts and orchestrator (Leader), testing and debug agents (Manar), memory and metrics (Safa), security agent (Haytam).
- **Task list:** long multi-step tasks tracked with Bob's to-do list (for example 13/21 on the orchestrator).
- **Code review with Bob:** Safa's review task (20).
- The product itself also applies the same ideas: specialised agents, **parallel execution** of tests and security, and a human in the loop.

## What Bob did and what the team did

Bob wrote the first versions of the architecture, the contracts, the orchestrator and the individual agents. The Leader's orchestrator task hit the Bobcoin budget (40.23 Bobcoins used), so the remaining fixes, the integration of all agents, the tests, the API and the demo were finished by the team with another AI assistant (Claude). The plan agent replays a saved Bob Plan session and does not call Bob live. The build and fix agents are stubs. Nothing here presents a simulated run as Bob's work.
