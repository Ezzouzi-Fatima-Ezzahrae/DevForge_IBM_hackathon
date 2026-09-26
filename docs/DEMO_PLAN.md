# Demo plan (4 minutes)

One idea goes from nothing to a released, tested and secured project, with a human approving the release. **No live AI calls during the demo**: all agent outputs come from saved results, so nothing depends on the internet.

Before every run: `python tests/restore_demo_bug.py` (puts the two planted problems back), then start the backend and the dashboard.

## Script and speakers

| Time | Step | What the screen shows | Who speaks |
|---|---|---|---|
| 0:00 | The problem and what DevForge is | Slide: problem, idea, pipeline | Leader |
| 0:30 | Developer gives the idea | Dashboard, "task management SaaS", Start | Ali (drives the screen) |
| 0:45 | Research, requirements, architecture | PLAN card green: 6 user stories, stack, 3 decisions | Fati |
| 1:15 | Build, then tests fail | BUILD green, TEST red: 17/20 | Manar |
| 1:35 | Debugger finds and fixes the bug | DEBUG card: root cause, patch; TEST green 20/20; retry badge 1 | Manar |
| 1:55 | Security finds a vulnerability | SECURITY red: hard-coded secret, BLOCKED | Haytam |
| 2:15 | Fix and rescan | FIX card, SECURITY green | Haytam |
| 2:30 | Quality gates and human approval | Approval screen: all gates green, Approve | Leader (clicks) |
| 2:45 | Released | RELEASED | Leader |
| 3:00 | Memory and impact | Decision log, Impact panel with real numbers | Safa |
| 3:30 | Why it is more than a code generator, and how Bob was used | Slide: gates, loops, human in the loop, Bob evidence | Leader |
| 3:50 | Questions | | Everyone |

## Backup plans

- If a real agent fails: switch that stage to its stub (config flag or environment variable) and continue.
- If the dashboard fails: run `python scripts/demo.py` (offline terminal demo).
- Record a video of a full successful run before the freeze and keep it ready.

## Rehearsal rule

Four full rehearsals with the whole team in the last 8 hours, timed. After each one, write down what went wrong and fix only that.
