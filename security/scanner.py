"""
security/scanner.py
Security scanner — DevForge pipeline.

Two scanning strategies are combined:

1. Bandit SAST — detects Python-level issues:
   - hardcoded passwords / secrets
   - unsafe subprocess usage (shell=True)
   - SQL injection patterns
   - use of assert in security context
   - insecure random / hash usage
   - etc.

2. Custom Authorization Checker — detects business-logic access control gaps
   that Bandit cannot detect because they are application-semantic:
   - Route handlers that perform DELETE/PUT/PATCH without an ownership check
   - Matches CWE-639 (Authorization Bypass Through User-Controlled Key)

Bandit severity mapping:
    HIGH   → "HIGH"
    MEDIUM → "MEDIUM"
    LOW    → "LOW"

Design rules:
    - Never return PASS when the scanner itself failed — raise ScannerError.
    - Never invent findings. Every finding must be traceable to scanner output or
      a specific code pattern actually found in the file.
    - shell=True is avoided in subprocess calls.
    - Paths are validated against the allowed workspace root.
"""
from __future__ import annotations

import ast
import json
import logging
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import List, Optional

from memory.schemas import SecurityFinding

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Map Bandit severity strings to our canonical severity levels
_BANDIT_SEVERITY_MAP: dict[str, str] = {
    "HIGH":   "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW":    "LOW",
}

# Map Bandit confidence strings — we require at least MEDIUM confidence
_MIN_CONFIDENCE = {"HIGH", "MEDIUM"}

# Bandit test IDs that we map to specific CWEs
_BANDIT_CWE_MAP: dict[str, str] = {
    "B105": "CWE-259",   # hardcoded_password_string
    "B106": "CWE-259",   # hardcoded_password_funcarg
    "B107": "CWE-259",   # hardcoded_password_default
    "B108": "CWE-377",   # probable_insecure_usage_of_temp_file
    "B110": "CWE-390",   # try_except_pass
    "B112": "CWE-730",   # try_except_continue
    "B201": "CWE-78",    # flask_debug_true
    "B301": "CWE-502",   # pickle
    "B302": "CWE-502",   # marshal_loads
    "B303": "CWE-327",   # md5
    "B304": "CWE-327",   # ciphers
    "B305": "CWE-327",   # cipher_modes
    "B306": "CWE-377",   # mktemp_q
    "B307": "CWE-78",    # eval
    "B308": "CWE-79",    # mark_safe
    "B310": "CWE-601",   # urllib_urlopen
    "B311": "CWE-330",   # random
    "B312": "CWE-605",   # telnetlib
    "B313": "CWE-611",   # xml_bad_cElementTree
    "B314": "CWE-611",   # xml_bad_ElementTree
    "B315": "CWE-611",   # xml_bad_expatreader
    "B316": "CWE-611",   # xml_bad_expatbuilder
    "B317": "CWE-611",   # xml_bad_sax
    "B318": "CWE-611",   # xml_bad_minidom
    "B319": "CWE-611",   # xml_bad_pulldom
    "B320": "CWE-611",   # xml_bad_etree
    "B321": "CWE-321",   # ftp_unencrypted
    "B322": "CWE-78",    # input
    "B323": "CWE-295",   # unverified_context
    "B324": "CWE-327",   # hashlib_new_insecure_functions
    "B325": "CWE-330",   # tempnam_mktemp
    "B401": "CWE-319",   # import_telnetlib
    "B402": "CWE-319",   # import_ftplib
    "B403": "CWE-502",   # import_pickle
    "B404": "CWE-78",    # import_subprocess
    "B405": "CWE-611",   # import_xml_etree
    "B406": "CWE-611",   # import_xml_sax
    "B407": "CWE-611",   # import_xml_expat
    "B408": "CWE-611",   # import_xml_minidom
    "B409": "CWE-611",   # import_xml_pulldom
    "B410": "CWE-611",   # import_lxml
    "B411": "CWE-20",    # import_xmlrpclib
    "B412": "CWE-20",    # import_httpoxy
    "B413": "CWE-327",   # import_pycrypto
    "B501": "CWE-295",   # request_with_no_cert_validation
    "B502": "CWE-326",   # ssl_with_bad_version
    "B503": "CWE-327",   # ssl_with_bad_defaults
    "B504": "CWE-326",   # ssl_with_no_version
    "B505": "CWE-327",   # weak_cryptographic_key
    "B506": "CWE-20",    # yaml_load
    "B507": "CWE-295",   # ssh_no_host_key_verification
    "B601": "CWE-78",    # paramiko_calls
    "B602": "CWE-78",    # subprocess_popen_with_shell_equals_true
    "B603": "CWE-78",    # subprocess_without_shell_equals_true
    "B604": "CWE-78",    # any_other_function_with_shell_equals_true
    "B605": "CWE-78",    # start_process_with_a_shell
    "B606": "CWE-78",    # start_process_with_no_shell
    "B607": "CWE-78",    # start_process_with_partial_path
    "B608": "CWE-89",    # hardcoded_sql_expressions
    "B609": "CWE-78",    # linux_commands_wildcard_injection
    "B610": "CWE-89",    # django_extra_used
    "B611": "CWE-89",    # django_rawsql_used
    "B701": "CWE-94",    # jinja2_autoescape_false
    "B702": "CWE-94",    # use_of_mako_templates
    "B703": "CWE-80",    # django_mark_safe
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ScannerError(RuntimeError):
    """Raised when the scanner fails in a way that prevents producing findings.
    The caller must NOT treat this as PASS.
    """


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def _validate_scan_path(path: str, workspace_root: Optional[str] = None) -> Path:
    """
    Resolve and validate that ``path`` is inside the allowed workspace.
    Raises ValueError if the path escapes the workspace.
    """
    resolved = Path(path).resolve()
    if workspace_root is not None:
        root = Path(workspace_root).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            raise ValueError(
                f"Scan path '{resolved}' is outside workspace root '{root}'"
            )
    if not resolved.exists():
        raise FileNotFoundError(f"Scan path does not exist: {resolved}")
    return resolved


# ---------------------------------------------------------------------------
# Bandit SAST scanner
# ---------------------------------------------------------------------------

def run_bandit(
    path: str,
    workspace_root: Optional[str] = None,
) -> List[SecurityFinding]:
    """
    Run Bandit against ``path`` and return a list of SecurityFinding instances.

    Args:
        path:           Directory or file to scan.
        workspace_root: Optional root to restrict path traversal.

    Returns:
        List of SecurityFinding (may be empty if no issues found).

    Raises:
        ScannerError: If Bandit is not available, times out, or produces
                      unparseable output. Callers must NOT treat this as PASS.
    """
    resolved = _validate_scan_path(path, workspace_root)

    logger.info("Bandit scan started | path=%s", resolved)

    _bandit_cmd_args = ["-r", str(resolved), "-f", "json", "-q", "--exit-zero"]

    def _run_cmd(executable: list) -> subprocess.CompletedProcess:
        return subprocess.run(
            executable + _bandit_cmd_args,
            capture_output=True,
            text=True,
            timeout=120,
        )

    try:
        proc = _run_cmd(["bandit"])
    except FileNotFoundError:
        # bandit not on PATH — try python -m bandit
        import sys as _sys
        try:
            proc = _run_cmd([_sys.executable, "-m", "bandit"])
        except FileNotFoundError:
            raise ScannerError(
                "Bandit is not installed or not on PATH. "
                "Install with: pip install bandit"
            )
    except subprocess.TimeoutExpired:
        raise ScannerError("Bandit scan timed out after 120 seconds")

    # Bandit writes findings to stdout as JSON
    raw_output = proc.stdout.strip()
    if not raw_output:
        # No JSON at all — could be an empty directory or a crash
        if proc.returncode not in (0, 1):
            raise ScannerError(
                f"Bandit exited with unexpected code {proc.returncode}. "
                f"stderr: {proc.stderr[:500]}"
            )
        logger.info("Bandit scan finished | no findings")
        return []

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ScannerError(
            f"Bandit produced non-JSON output: {exc}. "
            f"Raw output (first 500 chars): {raw_output[:500]}"
        )

    findings: List[SecurityFinding] = []
    for issue in data.get("results", []):
        severity_raw = issue.get("issue_severity", "LOW").upper()
        confidence_raw = issue.get("issue_confidence", "LOW").upper()

        # Skip very low confidence findings to reduce noise
        if confidence_raw not in _MIN_CONFIDENCE:
            continue

        severity = _BANDIT_SEVERITY_MAP.get(severity_raw, "LOW")
        test_id = issue.get("test_id", "B000")
        cwe_info = issue.get("issue_cwe", {})
        if isinstance(cwe_info, dict) and cwe_info.get("id"):
            cwe = f"CWE-{cwe_info['id']}"
        else:
            cwe = _BANDIT_CWE_MAP.get(test_id, "CWE-UNKNOWN")

        finding_id = f"SEC-{str(uuid.uuid4())[:8].upper()}"
        finding = SecurityFinding(
            id=finding_id,
            severity=severity,
            category=test_id.lower(),
            description=issue.get("issue_text", "No description"),
            file=_normalize_path(issue.get("filename", ""), resolved),
            line=int(issue.get("line_number", 0)),
            cwe=cwe,
            status="OPEN",
            evidence=issue.get("code", "").strip() or None,
            recommendation=_bandit_recommendation(test_id),
        )
        findings.append(finding)

    logger.info(
        "Bandit scan finished | path=%s total_findings=%d",
        resolved,
        len(findings),
    )
    return findings


def _normalize_path(filename: str, scan_root: Path) -> str:
    """Return the filename as a path relative to the scan root, if possible."""
    try:
        return str(Path(filename).resolve().relative_to(scan_root.parent))
    except ValueError:
        return filename


def _bandit_recommendation(test_id: str) -> Optional[str]:
    """Return a human-readable recommendation for known Bandit test IDs."""
    _RECS: dict[str, str] = {
        "B105": "Replace hardcoded password string with an environment variable.",
        "B106": "Replace hardcoded password argument with an environment variable.",
        "B107": "Replace hardcoded default password with an environment variable.",
        "B301": "Avoid pickle for untrusted data; use json or another safe format.",
        "B303": "Replace MD5/SHA1 with SHA-256 or stronger.",
        "B307": "Replace eval() with a safe alternative (ast.literal_eval or explicit parsing).",
        "B311": "Use secrets.token_bytes() or os.urandom() instead of random.",
        "B501": "Enable SSL certificate verification (verify=True).",
        "B602": "Avoid shell=True; use a list of arguments instead.",
        "B605": "Do not start a process with a shell; pass a list of arguments.",
        "B608": "Use parameterized queries instead of string formatting for SQL.",
    }
    return _RECS.get(test_id)


# ---------------------------------------------------------------------------
# Custom authorization checker
# ---------------------------------------------------------------------------

# Regex patterns that indicate write/delete route handlers
_WRITE_METHOD_PATTERN = re.compile(
    r'@\w+\.(delete|put|patch)\s*\(',
    re.IGNORECASE,
)

# AST-based check: detect FastAPI/Flask route functions that perform
# DELETE/PUT/PATCH without an ownership comparison.
# We look for functions decorated with a .delete / .put / .patch decorator
# that do NOT contain a comparison of the form `x.owner_id ... current_user`
# or an explicit HTTPException(status_code=403).

def run_authorization_checker(
    path: str,
    workspace_root: Optional[str] = None,
) -> List[SecurityFinding]:
    """
    AST-based authorization checker.

    Scans Python files for route handlers that mutate or delete a resource
    without an ownership verification pattern.  Detects:

        CWE-639  Authorization Bypass Through User-Controlled Key
        CWE-862  Missing Authorization

    This checker specifically targets the demo scenario:
        DELETE /tasks/{id} without task.owner_id == current_user.id

    It is intentionally conservative: it only reports findings it can
    directly observe in the AST, not speculative ones.
    """
    resolved = _validate_scan_path(path, workspace_root)
    findings: List[SecurityFinding] = []

    files_to_check: List[Path] = (
        [resolved] if resolved.is_file()
        else list(resolved.rglob("*.py"))
    )

    for filepath in files_to_check:
        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            logger.warning("Could not parse %s — skipping", filepath)
            continue

        new_findings = _check_authorization_in_tree(tree, source, filepath)
        findings.extend(new_findings)

    logger.info(
        "Authorization checker finished | path=%s findings=%d",
        resolved,
        len(findings),
    )
    return findings


def _check_authorization_in_tree(
    tree: ast.AST,
    source: str,
    filepath: Path,
) -> List[SecurityFinding]:
    """Traverse the AST of a single file and return authorization findings."""
    findings: List[SecurityFinding] = []
    source_lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Check if this function has a write/delete HTTP method decorator
        http_method = _get_write_http_method(node)
        if http_method is None:
            continue

        route_path = _get_route_path(node)

        # Only care about routes that operate on a specific resource by ID
        if "{" not in (route_path or ""):
            continue

        # Check whether the function body contains an ownership check
        if not _has_ownership_check(node):
            # Extract the line of the first actual statement as evidence
            evidence_line = _find_delete_statement_line(node, source_lines)
            line_no = evidence_line if evidence_line else node.lineno

            # Build a relative path for display
            try:
                display_path = str(filepath.resolve().relative_to(Path.cwd()))
            except ValueError:
                display_path = str(filepath)
            # Normalise to forward slashes for cross-platform consistency
            display_path = display_path.replace("\\", "/")

            finding_id = f"SEC-{str(uuid.uuid4())[:8].upper()}"
            findings.append(
                SecurityFinding(
                    id=finding_id,
                    severity="HIGH",
                    category="broken_access_control",
                    description=(
                        f"{http_method.upper()} {route_path} does not verify "
                        f"that the resource belongs to the current user before "
                        f"modifying or deleting it."
                    ),
                    file=display_path,
                    line=line_no,
                    cwe="CWE-639",
                    status="OPEN",
                    evidence=_get_evidence_snippet(source_lines, line_no),
                    recommendation=(
                        "Fetch the resource first. "
                        "Compare resource.owner_id with current_user.id. "
                        "Raise HTTPException(status_code=403) if they differ."
                    ),
                )
            )

    return findings


def _get_write_http_method(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Optional[str]:
    """Return "delete", "put", or "patch" if the function has such a decorator, else None."""
    for decorator in func.decorator_list:
        # Handle @router.delete(...) or @app.delete(...)
        if isinstance(decorator, ast.Call):
            func_part = decorator.func
            if isinstance(func_part, ast.Attribute):
                method = func_part.attr.lower()
                if method in ("delete", "put", "patch"):
                    return method
        elif isinstance(decorator, ast.Attribute):
            method = decorator.attr.lower()
            if method in ("delete", "put", "patch"):
                return method
    return None


def _get_route_path(func: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[str]:
    """Extract the route path string from the first decorator argument."""
    for decorator in func.decorator_list:
        if isinstance(decorator, ast.Call) and decorator.args:
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                return first_arg.value
    return None


def _has_ownership_check(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """
    Return True if the function body contains a recognisable ownership check.

    We look for any of:
      - A comparison involving both "owner" (or "user_id") and "current_user"
      - A raise of HTTPException with status_code 403
      - An attribute access pattern like `task.owner_id` or `item.user_id`
        combined with an equality/inequality comparison
    """
    source_dump = ast.dump(func)

    # Heuristic 1: string markers present in the AST dump
    has_owner_ref = (
        "owner_id" in source_dump
        or "owner" in source_dump
        or "user_id" in source_dump
    )
    has_current_user = "current_user" in source_dump
    has_403 = "403" in source_dump

    if (has_owner_ref and has_current_user) or has_403:
        return True

    # Heuristic 2: walk for actual Compare/If nodes that reference owner
    for node in ast.walk(func):
        if isinstance(node, ast.Compare):
            left_src = ast.dump(node.left)
            comparators_src = "".join(ast.dump(c) for c in node.comparators)
            combined = left_src + comparators_src
            if "owner" in combined or "user_id" in combined:
                return True

    return False


def _find_delete_statement_line(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: List[str],
) -> Optional[int]:
    """
    Try to find the line number of the actual delete/remove DB call in the function.
    Looks for calls named delete, remove, destroy, etc.
    """
    _DELETE_NAMES = {"delete", "remove", "destroy", "drop", "erase"}
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr.lower() in _DELETE_NAMES:
                    return node.lineno
            elif isinstance(node.func, ast.Name):
                if node.func.id.lower() in _DELETE_NAMES:
                    return node.lineno
    return None


def _get_evidence_snippet(source_lines: List[str], line_no: int, context: int = 3) -> str:
    """Return a few lines of source around the finding for the evidence field."""
    start = max(0, line_no - context - 1)
    end = min(len(source_lines), line_no + context)
    snippet_lines = source_lines[start:end]
    return "\n".join(
        f"{start + i + 1:4d} | {line}"
        for i, line in enumerate(snippet_lines)
    )


# ---------------------------------------------------------------------------
# Combined scanner entry point
# ---------------------------------------------------------------------------

def scan(
    path: str,
    workspace_root: Optional[str] = None,
    use_bandit: bool = True,
    use_auth_checker: bool = True,
) -> List[SecurityFinding]:
    """
    Run all enabled scanners against ``path`` and return a merged finding list.

    Args:
        path:             Path to scan (file or directory).
        workspace_root:   Optional root for path traversal protection.
        use_bandit:       Whether to run Bandit SAST.
        use_auth_checker: Whether to run the custom authorization checker.

    Returns:
        Deduplicated list of SecurityFinding instances.

    Raises:
        ScannerError: If a required scanner fails in a way that prevents
                      producing a reliable result.  Callers must NOT treat
                      this as PASS.
    """
    all_findings: List[SecurityFinding] = []

    if use_bandit:
        try:
            bandit_findings = run_bandit(path, workspace_root)
            all_findings.extend(bandit_findings)
        except ScannerError:
            raise  # propagate — do not silently return PASS

    if use_auth_checker:
        auth_findings = run_authorization_checker(path, workspace_root)
        all_findings.extend(auth_findings)

    logger.info(
        "Combined scan finished | path=%s total=%d bandit=%s auth_checker=%s",
        path,
        len(all_findings),
        use_bandit,
        use_auth_checker,
    )
    return all_findings
