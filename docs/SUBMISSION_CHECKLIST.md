# Submission checklist (IBM Bob 2.0 Hackathon, lablab.ai)

Requirements come from the hackathon guide and the lablab event page. The 12 form fields and the deadline (Sun 27 Sep 2026, 11:00 AM EDT = 16:00 in Casablanca) come from a third-party tracker: **confirm them on the lablab submission form**. Check every item on a fresh clone of `main`.

## Required by the guide
- [ ] Working prototype built with IBM Bob IDE as a core component
- [ ] Public code repository (open the URL in a private window)
- [ ] `bob_sessions/` folder with Bob task-session summary screenshots, PNG, named `teamname_taskXX_description.png`, from each team member (see `bob_sessions/README.md`)
- [ ] No client data, personal data or confidential data in the repository

## The 12 lablab fields (text drafts in `docs/SUBMISSION_TEXT.md`)
- [ ] Project title
- [ ] Short description
- [ ] Long description
- [ ] IBM Bob usage statement
- [ ] Technology and category tags
- [ ] Public code repository URL
- [ ] Bob task-session screenshots (in the repository)
- [ ] Demo application platform
- [ ] Application URL (hosted, or the closest available link)
- [ ] Cover image (`docs/cover.png`)
- [ ] Video demonstration (script: `docs/VIDEO_SCRIPT.md`, 5 minutes)
- [ ] Slide presentation (`docs/DevForge_Slides.pptx`, exported to PDF if the form asks)

## Judging criteria (from the tracker) and where we answer them
| Criterion | Our answer |
|---|---|
| Application of technology (a clear use of Bob 2.0) | `bob_sessions/` index, slides 6 and 7, Bob usage statement |
| Presentation | video, slides, narrated demo, cover image |
| Business value | slide 8 (target user, market, revenue model), slide 9, `docs/IMPACT.md` (measured numbers only) |
| Originality | orchestrator with gates and loops, parallel checks, human in the loop, honest labels |

## The repository
- [ ] `README.md` explains problem, solution, architecture, how to run
- [ ] `requirements.txt` installs on a clean machine
- [ ] `.env.example` has names only; no secrets (`git grep -i -E "secret|password|token|api_key"`)
- [ ] `backend/demo_bug.py` is the **buggy** version (`python tests/restore_demo_bug.py`)
- [ ] `logs/`, `data/` and `memory/data/*.json` are not committed
- [ ] `DATA_SOURCES.md` lists the real sources
- [ ] `docs/STATUS.md` is current

## It works (fresh clone)
- [ ] `python -m pytest -q` passes
- [ ] `python scripts/demo.py --auto-approve` ends in RELEASED, twice in a row
- [ ] `uvicorn backend.main:app` starts; a run reaches RELEASED through the API
- [ ] Each real agent has a working stub fallback
- [ ] The retry limits work: the pipeline ends in FAILED, not in a loop

## Honesty
- [ ] The plan agent is described as a replay of a saved Bob Plan session
- [ ] Build and fix are described as stubs
- [ ] No simulated run is presented as Bob's work
- [ ] The Impact numbers come from real runs only

## Team
- [ ] Every member's work is merged into `main`
- [ ] Every member has at least one Bob screenshot in `bob_sessions/`
- [ ] Slides finished; each speaker knows their part
- [ ] Final `git pull` on the demo machine
