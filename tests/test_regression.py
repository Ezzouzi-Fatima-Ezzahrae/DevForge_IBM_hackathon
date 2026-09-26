import subprocess
import sys
from pathlib import Path


def test_regression_after_security_fix():
    """The functional tests must remain 20/20 after the security fix."""
    project_root = Path(__file__).resolve().parents[1]
    bug_file = project_root / "backend" / "demo_bug.py"

    source = bug_file.read_text(encoding="utf-8")

    # Simulate Haytam's security fix by removing the hard-coded secret.
    fixed_source = source.replace(
        'API_SECRET_KEY = "hardcoded-demo-secret"\n\n',
        "",
    )

    bug_file.write_text(fixed_source, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_demo_tasks.py", "-q"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert "20 passed" in result.stdout
    finally:
        # Restore the complete planted-bug version.
        restore = subprocess.run(
            [sys.executable, "tests/restore_demo_bug.py"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert restore.returncode == 0
