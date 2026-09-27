# Leader: next tasks

## Done
Architecture, contracts, orchestrator (gates, retries, parallel checks), approval broker, gate tests (also fixed: 0 tests never passes), memory wiring, offline demo (`scripts/demo.py`), README with diagram, slides (`DevForge_Slides.pptx`), review of the backend (three fixes and API flow tests), fresh-clone test (128 tests, demo twice, API to RELEASED), status update.

## To do, in order

1. **Review and merge** each PR as it arrives: Haytam (fix agent and secret rule together), Fati (dashboard), Safa (insights), Manar. After each merge run `python -m pytest -q` on `main`, then register Haytam's fix agent in `agents_base.py` (`fix` stage, with a stub fallback).
2. **Set the cut-off time** and announce it. If the page is not merged by then, the demo is the terminal version.
3. **Backup video:** `python scripts/demo.py --auto-approve --no-memory` (and the dashboard if it works).
4. **Update slides and STATUS** to what was merged (slide 5 real vs stub, slide 7 numbers from Safa's runs).
5. **Clean-up:** remove the old placeholders (Next.js files, docker-compose, old routers).
6. **Fresh-clone test** on the final `main` (`docs/SUBMISSION_CHECKLIST.md`), then Bob evidence check for the whole team.
7. **Two timed rehearsals** with `docs/DEMO_PLAN.md`; then freeze and submit (verify the required format and deadline).
