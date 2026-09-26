"""
tests/conftest.py
Shared test setup.

- Memory and metrics recording is OFF by default in tests (so tests do not write into
  memory/data/). Tests that need it switch it on and redirect the files to a temp folder.
- backend/demo_bug.py is put back after the test session. Some pipeline tests run the
  real debug agent, which patches that file; the demo needs the buggy version.
"""
import os
from pathlib import Path

import pytest

os.environ.setdefault("DEVFORGE_MEMORY", "off")

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _keep_demo_bug_file_unchanged():
    target = ROOT / "backend" / "demo_bug.py"
    original = target.read_bytes() if target.exists() else None
    yield
    if original is not None and target.read_bytes() != original:
        target.write_bytes(original)
