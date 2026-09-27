# Video script (5 minutes), built on the lablab judging advice

Structure recommended by lablab: 0:00-0:30 problem, 0:30-2:30 live demo, 2:30-4:00 business case, 4:00-5:00 team and roadmap. Judges reward clarity over production value: show the working demo early. Speak at a calm pace (about 140 words a minute). Slide numbers refer to `docs/DevForge_Slides.pptx` (10 slides).

## Before recording
1. `git pull origin main`, then `python tests/restore_demo_bug.py`.
2. Windows Terminal or PowerShell, dark background, large font (Ctrl + mouse wheel), window maximised. Test once: `python scripts/demo.py --pause 1.6`.
3. Record the screen with Xbox Game Bar (Win + Alt + R) or OBS, 1080p, microphone on. Do a 10-second test first and listen to it.
4. Close notifications. Have the slides open in slideshow mode (F5) and the terminal ready in another window.
5. Record in one take if you can. If something breaks, stop and redo that segment: a clear short retake is better than a perfect long one.

## 0:00 to 0:30 | Problem | slide 2
"AI can write code very fast. But nobody proves it works, nobody checks that it is safe, and nobody decides who may release it. If you lead a small team that ships AI-written code, you still spend hours coordinating tests, debugging, security review and release. We built DevForge to close that gap."

## 0:30 to 0:45 | The idea | slide 3
"DevForge is not a code generator. It is an orchestrator. Specialised agents plan, build, test, debug and scan the code. Quality gates decide if the project may move on. Failures loop back to the right agent, and only a human can release."

## 0:45 to 2:30 | Live demo | terminal, `python scripts/demo.py --pause 1.6`
Say each line while the matching step appears. Press **y** yourself at both approvals.
- Banner and plan (about 0:50): "We give it one idea: a task management SaaS. The plan agent produces requirements and an architecture, and the plan gate checks them: six user stories, three architecture decisions."
- First approval: "First human decision: I approve the architecture."
- Test and security (about 1:10): "Tests and the security scan run in parallel. The tests fail: 17 out of 20. The security agent finds the same flaw, a HIGH access-control issue: any user can delete another user's task. The security gate is blocked."
- Debug (about 1:35): "The Debugger finds the root cause and patches the real file. You can see the exact change: an ownership check."
- Re-test (about 1:55): "We test and scan again: 20 out of 20, and the security gate passes."
- Second approval (about 2:10): "Second human decision: all gates are green, and I approve the release."
- Result card (about 2:20): "Released. Two retries, two human approvals. Every agent is labelled: real, replay or stub, so nothing is hidden."

## 2:30 to 2:50 | Honesty | slide 5
"To be transparent: the orchestrator, the test, debug and security agents and the API are real. The plan agent replays a saved Bob plan, and build and fix are stubs today."

## 2:50 to 3:15 | IBM Bob | slides 6 and 7
"We used IBM Bob for the architecture in Plan mode, and Agent mode for the contracts, the orchestrator and every teammate's agent, with Bob's task list on long tasks. The evidence is in our repository: 21 task screenshots and a session note per member, including this consumption summary. Bob reached its budget during the orchestrator, so the team finished the integration, and we say so openly."

## 3:15 to 4:00 | Business case | slides 8 and 9
"Our user is a team lead who ships AI-written code. There are about 36 and a half million professional developers worldwide. As an illustration, one percent paying twenty dollars per seat per month would be about 88 million dollars a year; that is our assumption, not a measurement. Revenue comes from team seats, usage per pipeline run in CI, and a self-hosted enterprise plan. The value: less manual effort and rework, and fewer defects reaching release. The same flaw is caught twice, by the tests and by the scan. We measured 134 passing tests and three identical real runs, and we list our limits."

## 4:00 to 5:00 | Team and roadmap | slide 10
"We are five people. Fatima leads the orchestrator and integration, Fati built the plan agent, Manar the testing and debug agents and the API, Haytam the security agent, and Safa the memory and metrics. Next: a hosted dashboard with live approval, AI-backed builder, debugger and fix agents behind the same contracts, more gates, and a GitHub Action that runs DevForge on every pull request. Thank you."

## After recording
- Watch it once at normal speed. Check that the terminal text is readable and the audio is clear.
- Upload it (YouTube unlisted or the lablab form) and put the link in the submission form.
- Keep a copy of the video file in a safe place, not only in the repository.
