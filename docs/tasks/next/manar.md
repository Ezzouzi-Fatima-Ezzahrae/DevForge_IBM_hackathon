# Manar: next tasks

**Branch:** a new branch from the latest `main`. **Files:** `backend/`, `agents/testing_agent`, `agents/debug_agent`, `tests/`.

## Done (merged)
Real testing agent (17/20), real debug agent (patch and rerun, 20/20), restore script, second planted bug (hard-coded secret), test clean-up, and the **backend API** (create, start, status, approve, reset; the Leader added: wrong-gate approval refused, safe state read, bug restored on start, and `tests/test_api_flow.py`).

## To do, in order

1. **Insights endpoints, only if Safa has not pushed them** (ask her first): `GET /projects/{id}/decisions|gates|metrics|tests|security` in a router included from `backend/main.py`. Shapes are in `docs/API.md`.
2. **Tests:** one more `TestClient` test for `/reset` and one for a second `POST /start` on a running project.
3. **Clean-up:** done by the Leader (unused placeholders removed).
4. **Regression after the security fix:** when Haytam's fix agent lands, the tests must still be 20/20 (`tests/test_regression.py`).
5. **Demo:** explain the 17/20, root cause, patch and 20/20 in 30 seconds.

## Done when
`uvicorn backend.main:app` starts on a fresh clone, one run reaches RELEASED through the API, and `python -m pytest -q` passes.

## Talk to
Fati (the page uses your API), Safa (insights), Haytam (the second bug line), Leader.
