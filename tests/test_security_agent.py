"""
tests/test_security_agent.py
Tests for:
  1. scanner.run_hardcoded_secret_checker  — HIGH severity rule for secrets
  2. security.fix_agent.fix_hardcoded_secret — replaces hard-coded values
"""
from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from security.scanner import (
    _check_hardcoded_secrets_in_tree,
    run_hardcoded_secret_checker,
    scan,
)
from security.fix_agent import fix_hardcoded_secret


# ===========================================================================
# Helpers
# ===========================================================================

def _write_tmp(tmp_path: Path, filename: str, source: str) -> Path:
    """Write *source* to *tmp_path/filename* and return the Path."""
    p = tmp_path / filename
    p.write_text(textwrap.dedent(source), encoding="utf-8")
    return p


# ===========================================================================
# 1 — Hardcoded-secret scanner: unit-level (_check_hardcoded_secrets_in_tree)
# ===========================================================================

class TestHardcodedSecretCheckerAST:
    """Tests that exercise _check_hardcoded_secrets_in_tree directly."""

    def _parse(self, source: str):
        import ast
        return ast.parse(textwrap.dedent(source))

    def _check(self, source: str, filepath: Path):
        import ast
        src = textwrap.dedent(source)
        tree = ast.parse(src)
        lines = src.splitlines()
        return _check_hardcoded_secrets_in_tree(tree, lines, filepath)

    def test_api_secret_key_detected(self, tmp_path):
        """API_SECRET_KEY = "value" must produce one HIGH finding."""
        f = tmp_path / "demo.py"
        findings = self._check(
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
            f,
        )
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"
        assert findings[0].cwe == "CWE-798"
        assert findings[0].category == "hardcoded_secret"
        assert "API_SECRET_KEY" in findings[0].description

    def test_password_variable_detected(self, tmp_path):
        """DB_PASSWORD = "secret" → HIGH finding."""
        f = tmp_path / "config.py"
        findings = self._check('DB_PASSWORD = "hunter2"\n', f)
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"

    def test_token_variable_detected(self, tmp_path):
        """ACCESS_TOKEN = "abc123" → HIGH finding."""
        f = tmp_path / "auth.py"
        findings = self._check('ACCESS_TOKEN = "abc123"\n', f)
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"

    def test_key_suffix_detected(self, tmp_path):
        """STRIPE_SECRET_KEY = "sk_live_..." → HIGH finding."""
        f = tmp_path / "payments.py"
        findings = self._check('STRIPE_SECRET_KEY = "sk_live_xyz"\n', f)
        assert len(findings) == 1

    def test_env_var_call_not_flagged(self, tmp_path):
        """os.environ.get(...) is not a string literal — must not be flagged."""
        f = tmp_path / "safe.py"
        findings = self._check(
            'import os\nAPI_SECRET_KEY = os.environ.get("API_SECRET_KEY")\n',
            f,
        )
        assert findings == []

    def test_non_secret_variable_not_flagged(self, tmp_path):
        """DISPLAY_NAME = "Alice" must not be flagged (no secret keyword)."""
        f = tmp_path / "ui.py"
        findings = self._check('DISPLAY_NAME = "Alice"\n', f)
        assert findings == []

    def test_empty_string_not_flagged(self, tmp_path):
        """API_SECRET_KEY = "" (empty) must not be flagged."""
        f = tmp_path / "empty.py"
        findings = self._check('API_SECRET_KEY = ""\n', f)
        assert findings == []

    def test_integer_value_not_flagged(self, tmp_path):
        """SECRET_COUNT = 42 is not a string literal — not flagged."""
        f = tmp_path / "count.py"
        findings = self._check('SECRET_COUNT = 42\n', f)
        assert findings == []

    def test_multiple_secrets_all_detected(self, tmp_path):
        """Two different secret assignments → two findings."""
        f = tmp_path / "multi.py"
        source = 'API_KEY = "abc"\nDB_PASSWORD = "xyz"\n'
        findings = self._check(source, f)
        assert len(findings) == 2
        severities = {x.severity for x in findings}
        assert severities == {"HIGH"}

    def test_finding_line_number_is_correct(self, tmp_path):
        """The finding's line number must match the assignment line."""
        f = tmp_path / "demo.py"
        source = "# comment\n\nAPI_SECRET_KEY = \"s3cr3t\"\n"
        findings = self._check(source, f)
        assert len(findings) == 1
        assert findings[0].line == 3

    def test_recommendation_mentions_environ(self, tmp_path):
        """The recommendation must mention os.environ.get."""
        f = tmp_path / "demo.py"
        findings = self._check('MY_TOKEN = "tok"\n', f)
        assert len(findings) == 1
        assert "os.environ.get" in (findings[0].recommendation or "")


# ===========================================================================
# 2 — Hardcoded-secret scanner: integration (run_hardcoded_secret_checker)
# ===========================================================================

class TestRunHardcodedSecretChecker:

    def test_detects_secret_in_demo_bug(self, tmp_path):
        """run_hardcoded_secret_checker finds the planted secret in demo_bug.py."""
        demo = _write_tmp(
            tmp_path,
            "demo_bug.py",
            """\
            API_SECRET_KEY = "hardcoded-demo-secret"
            """,
        )
        findings = run_hardcoded_secret_checker(str(demo))
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"
        assert findings[0].cwe == "CWE-798"

    def test_clean_file_no_findings(self, tmp_path):
        """A file with no hardcoded secrets produces no findings."""
        safe = _write_tmp(
            tmp_path,
            "safe.py",
            """\
            import os
            API_SECRET_KEY = os.environ.get("API_SECRET_KEY")
            """,
        )
        findings = run_hardcoded_secret_checker(str(safe))
        assert findings == []

    def test_scans_directory_recursively(self, tmp_path):
        """Finds secrets in nested subdirectories."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        _write_tmp(sub, "config.py", 'DB_PASSWORD = "letmein"\n')
        findings = run_hardcoded_secret_checker(str(tmp_path))
        assert any(f.severity == "HIGH" for f in findings)

    def test_syntax_error_file_skipped(self, tmp_path):
        """A file with a syntax error is skipped — no ScannerError raised."""
        bad = tmp_path / "bad.py"
        bad.write_text("def broken(\n", encoding="utf-8")
        # Should complete without exception
        findings = run_hardcoded_secret_checker(str(tmp_path))
        # bad.py has no valid assignments — no findings from it
        assert isinstance(findings, list)

    def test_secret_checker_finding_is_open(self, tmp_path):
        """Findings from the checker must have status=OPEN."""
        f = _write_tmp(tmp_path, "demo.py", 'API_KEY = "abc123"\n')
        findings = run_hardcoded_secret_checker(str(f))
        assert findings[0].status == "OPEN"


# ===========================================================================
# 3 — scan() integration: secret checker wired into combined scan
# ===========================================================================

class TestScanIntegration:

    def test_scan_detects_secret_as_high(self, tmp_path):
        """scan() with use_secret_checker=True rates a hardcoded secret as HIGH."""
        demo = _write_tmp(
            tmp_path,
            "demo_bug.py",
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
        )
        # Disable bandit to avoid subprocess dependency in unit tests
        findings = scan(
            str(demo),
            use_bandit=False,
            use_auth_checker=False,
            use_secret_checker=True,
        )
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"
        assert findings[0].cwe == "CWE-798"

    def test_scan_secret_checker_disabled_no_extra_findings(self, tmp_path):
        """scan() with use_secret_checker=False does not add the HIGH finding."""
        demo = _write_tmp(
            tmp_path,
            "demo_bug.py",
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
        )
        findings = scan(
            str(demo),
            use_bandit=False,
            use_auth_checker=False,
            use_secret_checker=False,
        )
        assert findings == []

    def test_scan_secret_checker_enabled_by_default(self, tmp_path):
        """scan() enables the secret checker by default."""
        demo = _write_tmp(
            tmp_path,
            "demo_bug.py",
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
        )
        # Only way to know default is True: call without the flag and check
        # that a HIGH finding is produced (when bandit + auth off for speed)
        import inspect
        from security.scanner import scan as _scan
        sig = inspect.signature(_scan)
        assert sig.parameters["use_secret_checker"].default is True


# ===========================================================================
# 4 — fix_agent.fix_hardcoded_secret
# ===========================================================================

class TestFixHardcodedSecret:

    def test_fixes_hardcoded_value(self, tmp_path):
        """The fix agent replaces a hard-coded value with os.environ.get(...)."""
        target = _write_tmp(
            tmp_path,
            "demo_bug.py",
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
        )
        result = fix_hardcoded_secret({
            "file": str(target),
            "line": 1,
            "var_name": "API_SECRET_KEY",
        })
        assert result["status"] == "FIXED"
        patched_source = target.read_text(encoding="utf-8")
        assert 'os.environ.get("API_SECRET_KEY")' in patched_source
        assert '"hardcoded-demo-secret"' not in patched_source

    def test_patched_field_in_result(self, tmp_path):
        """result['patched'] contains the replacement line."""
        target = _write_tmp(
            tmp_path,
            "demo_bug.py",
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
        )
        result = fix_hardcoded_secret({
            "file": str(target),
            "line": 1,
            "var_name": "API_SECRET_KEY",
        })
        assert result["patched"] is not None
        assert "os.environ.get" in result["patched"]

    def test_original_field_in_result(self, tmp_path):
        """result['original'] contains the original assignment line."""
        target = _write_tmp(
            tmp_path,
            "demo_bug.py",
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
        )
        result = fix_hardcoded_secret({
            "file": str(target),
            "line": 1,
            "var_name": "API_SECRET_KEY",
        })
        assert "hardcoded-demo-secret" in result["original"]

    def test_import_os_inserted_when_missing(self, tmp_path):
        """If os is not imported, fix_agent inserts `import os`."""
        target = _write_tmp(
            tmp_path,
            "no_import.py",
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
        )
        fix_hardcoded_secret({
            "file": str(target),
            "line": 1,
            "var_name": "API_SECRET_KEY",
        })
        patched = target.read_text(encoding="utf-8")
        assert "import os" in patched

    def test_import_os_not_duplicated(self, tmp_path):
        """If os is already imported, fix_agent does not add a second import."""
        source = "import os\nAPI_SECRET_KEY = \"hardcoded-demo-secret\"\n"
        target = tmp_path / "with_import.py"
        target.write_text(source, encoding="utf-8")
        fix_hardcoded_secret({
            "file": str(target),
            "line": 2,
            "var_name": "API_SECRET_KEY",
        })
        patched = target.read_text(encoding="utf-8")
        assert patched.count("import os") == 1

    def test_already_fixed_returns_skipped(self, tmp_path):
        """Calling fix_agent on an already-fixed line returns SKIPPED."""
        source = 'import os\nAPI_SECRET_KEY = os.environ.get("API_SECRET_KEY")\n'
        target = tmp_path / "fixed.py"
        target.write_text(source, encoding="utf-8")
        result = fix_hardcoded_secret({
            "file": str(target),
            "line": 2,
            "var_name": "API_SECRET_KEY",
        })
        assert result["status"] == "SKIPPED"

    def test_wrong_var_name_returns_skipped(self, tmp_path):
        """If var_name doesn't match what's on the line, result is SKIPPED."""
        target = _write_tmp(
            tmp_path,
            "demo.py",
            'OTHER_KEY = "value"\n',
        )
        result = fix_hardcoded_secret({
            "file": str(target),
            "line": 1,
            "var_name": "API_SECRET_KEY",
        })
        assert result["status"] == "SKIPPED"

    def test_missing_file_returns_error(self, tmp_path):
        """A non-existent file path returns ERROR."""
        result = fix_hardcoded_secret({
            "file": str(tmp_path / "nonexistent.py"),
            "line": 1,
            "var_name": "API_SECRET_KEY",
        })
        assert result["status"] == "ERROR"

    def test_missing_file_key_returns_error(self):
        """Omitting 'file' returns ERROR."""
        result = fix_hardcoded_secret({"line": 1, "var_name": "API_SECRET_KEY"})
        assert result["status"] == "ERROR"

    def test_missing_line_key_returns_error(self, tmp_path):
        """Omitting 'line' returns ERROR."""
        target = _write_tmp(tmp_path, "demo.py", 'API_SECRET_KEY = "x"\n')
        result = fix_hardcoded_secret({"file": str(target), "var_name": "API_SECRET_KEY"})
        assert result["status"] == "ERROR"

    def test_missing_var_name_returns_error(self, tmp_path):
        """Omitting 'var_name' returns ERROR."""
        target = _write_tmp(tmp_path, "demo.py", 'API_SECRET_KEY = "x"\n')
        result = fix_hardcoded_secret({"file": str(target), "line": 1})
        assert result["status"] == "ERROR"

    def test_line_out_of_range_returns_error(self, tmp_path):
        """Line number beyond file length returns ERROR."""
        target = _write_tmp(tmp_path, "demo.py", 'API_SECRET_KEY = "x"\n')
        result = fix_hardcoded_secret({
            "file": str(target),
            "line": 999,
            "var_name": "API_SECRET_KEY",
        })
        assert result["status"] == "ERROR"

    def test_multiline_file_correct_line_patched(self, tmp_path):
        """Only the targeted line is modified; other non-secret lines are untouched."""
        source = (
            "import os\n"           # os already present — no extra import injected
            "# comment\n"
            "SOME_VAR = 123\n"
            'API_SECRET_KEY = "hardcoded-demo-secret"\n'
            "ANOTHER_VAR = True\n"
        )
        target = tmp_path / "multi.py"
        target.write_text(source, encoding="utf-8")
        fix_hardcoded_secret({
            "file": str(target),
            "line": 4,
            "var_name": "API_SECRET_KEY",
        })
        lines = target.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "import os"
        assert lines[1] == "# comment"
        assert lines[2] == "SOME_VAR = 123"
        assert 'os.environ.get("API_SECRET_KEY")' in lines[3]
        assert lines[4] == "ANOTHER_VAR = True"

    def test_fix_round_trip_on_real_demo_bug(self, tmp_path):
        """
        Full round-trip: scanner detects HIGH finding → fix agent patches it
        → scanner no longer finds the secret.
        """
        demo = _write_tmp(
            tmp_path,
            "demo_bug.py",
            'API_SECRET_KEY = "hardcoded-demo-secret"\n',
        )

        # Step 1: scanner detects it
        findings_before = run_hardcoded_secret_checker(str(demo))
        assert len(findings_before) == 1
        assert findings_before[0].severity == "HIGH"

        # Step 2: fix agent patches it
        result = fix_hardcoded_secret({
            "file": str(demo),
            "line": findings_before[0].line,
            "var_name": "API_SECRET_KEY",
        })
        assert result["status"] == "FIXED"

        # Step 3: scanner no longer finds the secret
        findings_after = run_hardcoded_secret_checker(str(demo))
        assert findings_after == []
