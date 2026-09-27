"""
security/fix_agent.py
Fix Agent — DevForge security pipeline.

Responsibility:
    Receive a SecurityFinding of category "hardcoded_secret" (CWE-798), locate
    the offending assignment in the target file, and replace the hard-coded
    string literal with os.environ.get("<VAR_NAME>").

Contract:
    Input dict (FixInput):
        {
            "file":     "backend/demo_bug.py",   # path to the file to fix
            "line":     4,                        # 1-based line number of the assignment
            "var_name": "API_SECRET_KEY",         # variable name to replace value for
        }

    Output dict (FixResult):
        {
            "status":   "FIXED" | "SKIPPED" | "ERROR",
            "message":  "...",
            "file":     "backend/demo_bug.py",
            "line":     4,
            "original": 'API_SECRET_KEY = "hardcoded-demo-secret"',
            "patched":  'API_SECRET_KEY = os.environ.get("API_SECRET_KEY")',
        }

    SKIPPED means the line no longer contains a bare string literal for that
    variable (the fix was already applied or the file changed).  The caller
    must treat SKIPPED as non-blocking.

    ERROR means the file could not be read or written; the caller should
    route to HUMAN_REVIEW.

Design rules:
    - Never overwrite a line that has already been fixed.
    - Never modify anything other than the targeted assignment value.
    - Never introduce a bare import; if os is not already imported the fix
      adds "import os" before the first non-comment, non-docstring line.
    - All file I/O errors surface as status="ERROR", not as exceptions.
    - No LLM or network calls — purely deterministic text transformation.
"""
from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Matches:  VAR_NAME = "some value"  or  VAR_NAME = 'some value'
# Group 1 = indentation + var name + equals, Group 2 = quote char, Group 3 = everything after
_HARDCODED_ASSIGNMENT_RE = re.compile(
    r'^(?P<prefix>\s*(?P<var>\w+)\s*=\s*)(?P<quote>["\'])(?P<value>[^"\']*?)(?P=quote)(?P<suffix>\s*(?:#.*)?)$'
)


def fix_hardcoded_secret(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Patch the hard-coded credential assignment identified by ``input_data``.

    See module docstring for full input / output contract.
    """
    file_path_str: Optional[str] = input_data.get("file")
    line_no: Optional[int] = input_data.get("line")
    var_name: Optional[str] = input_data.get("var_name")

    # ── Validate inputs ───────────────────────────────────────────────────
    if not file_path_str:
        return _error("'file' is required in input_data", file=file_path_str, line=line_no)
    if not line_no or not isinstance(line_no, int) or line_no < 1:
        return _error("'line' must be a positive integer", file=file_path_str, line=line_no)
    if not var_name or not isinstance(var_name, str):
        return _error("'var_name' is required in input_data", file=file_path_str, line=line_no)

    file_path = Path(file_path_str)
    if not file_path.exists():
        return _error(f"File not found: {file_path}", file=file_path_str, line=line_no)

    # ── Read file ─────────────────────────────────────────────────────────
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _error(f"Cannot read file: {exc}", file=file_path_str, line=line_no)

    lines = source.splitlines(keepends=True)
    if line_no > len(lines):
        return _error(
            f"Line {line_no} is out of range (file has {len(lines)} lines)",
            file=file_path_str,
            line=line_no,
        )

    target_line = lines[line_no - 1]
    original = target_line.rstrip("\n").rstrip("\r")

    # ── Check the line is still a hardcoded assignment ────────────────────
    m = _HARDCODED_ASSIGNMENT_RE.match(original)
    if not m or m.group("var") != var_name:
        # Already fixed or the line changed — skip gracefully
        logger.info(
            "fix_agent: line %d in %s no longer matches a hardcoded assignment "
            "for '%s' — skipping",
            line_no,
            file_path_str,
            var_name,
        )
        return {
            "status": "SKIPPED",
            "message": (
                f"Line {line_no} does not contain a bare string literal for "
                f"'{var_name}' — may already be fixed."
            ),
            "file": file_path_str,
            "line": line_no,
            "original": original,
            "patched": None,
        }

    # ── Build the replacement line ─────────────────────────────────────────
    suffix = m.group("suffix") or ""
    patched = f'{m.group("prefix")}os.environ.get("{var_name}"){suffix}'
    # Preserve the original line ending
    line_ending = "\r\n" if target_line.endswith("\r\n") else "\n"
    lines[line_no - 1] = patched + line_ending

    # ── Ensure `import os` is present ─────────────────────────────────────
    new_source = "".join(lines)
    if not _has_os_import(new_source):
        insert_at = _find_import_insertion_point(lines)
        lines.insert(insert_at, "import os\n")
        new_source = "".join(lines)
        logger.debug("fix_agent: inserted 'import os' at line %d", insert_at + 1)

    # ── Write back ────────────────────────────────────────────────────────
    try:
        file_path.write_text(new_source, encoding="utf-8")
    except OSError as exc:
        return _error(f"Cannot write file: {exc}", file=file_path_str, line=line_no)

    logger.info(
        "fix_agent: patched '%s' at %s:%d",
        var_name,
        file_path_str,
        line_no,
    )
    return {
        "status": "FIXED",
        "message": (
            f"Replaced hard-coded value of '{var_name}' with "
            f'os.environ.get("{var_name}") at {file_path_str}:{line_no}.'
        ),
        "file": file_path_str,
        "line": line_no,
        "original": original,
        "patched": patched,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_os_import(source: str) -> bool:
    """Return True if the source already imports `os`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # If we can't parse it, assume os is present to avoid double-import.
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os":
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "os":
                return True
    return False


def _find_import_insertion_point(lines: list[str]) -> int:
    """
    Return the 0-based index at which to insert `import os`.

    Strategy: skip the module docstring (if any) and any existing import lines,
    then insert just before the first non-import statement.  Falls back to 0.
    """
    in_docstring = False
    docstring_done = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip blank lines and shebang
        if not stripped or stripped.startswith("#") or stripped.startswith("#!/"):
            continue
        # Skip the module-level docstring
        if not docstring_done:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                    docstring_done = True  # single-line docstring
                    continue
                in_docstring = True
                continue
        if in_docstring:
            if '"""' in stripped or "'''" in stripped:
                in_docstring = False
                docstring_done = True
            continue
        # Insert after existing import / from-import lines
        if stripped.startswith("import ") or stripped.startswith("from "):
            continue
        return i
    return 0


def _error(message: str, file: Optional[str], line: Optional[int]) -> Dict[str, Any]:
    logger.error("fix_agent error | file=%s line=%s msg=%s", file, line, message)
    return {
        "status": "ERROR",
        "message": message,
        "file": file,
        "line": line,
        "original": None,
        "patched": None,
    }
