"""Collect redacted source-scan and dependency-audit evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.verification import StageResult

_SOURCE_LIMIT = 2 * 1024 * 1024
_AUDIT_LIMIT = 8 * 1024 * 1024
_ALLOWED_SUFFIXES = {".py", ".swift", ".cs", ".js", ".ts", ".tsx", ".jsx"}
_PRIVATE_COMPONENTS = {".env", ".cache", "cache", "data", "db", "database"}
_SECRET_VALUE = re.compile(
    r"(?i)(?:sk-[A-Za-z0-9_-]{16,}|"
    r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})|"
    r"(?:AKIA|ASIA)[A-Z0-9]{16}|"
    r"(?:secret|token|password|api[_-]?key)\s*[:=]\s*['\"][^'\"]{16,}['\"]|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
_TICKET = re.compile(r"(?:#\d+|\b[A-Z][A-Z0-9]+-\d+\b)")
_TODO = re.compile(r"\b(?:TODO|FIXME)\b", re.IGNORECASE)
_COMMENT = re.compile(r"(?://|#|/\*)")


def _finding(rule: str, path: str, line: int) -> dict[str, object]:
    return {"rule": rule, "path": path, "line": line}


def _is_test_path(path: str) -> bool:
    parts = Path(path).parts
    return any(part.lower() in {"test", "tests", "fixture", "fixtures"} for part in parts) or Path(path).name.lower().startswith(("test_", "tests_"))


def _has_private_component(path: Path) -> bool:
    return any(part.lower() in _PRIVATE_COMPONENTS or part.lower().startswith(".env.") or
               part.lower().endswith((".db", ".sqlite", ".sqlite3")) for part in path.parts)


def scan_source(root: Path, paths: tuple[str, ...]) -> tuple[dict[str, object], ...]:
    """Scan explicitly requested in-root source files and return metadata only."""
    findings: list[dict[str, object]] = []
    try:
        base = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return (_finding("scan-error", ".", 0),)

    for requested in paths:
        try:
            if not isinstance(requested, str):
                raise ValueError
            relative = Path(requested)
            if relative.is_absolute() or not requested or ".." in relative.parts or "\x00" in requested or _has_private_component(relative):
                raise ValueError
            candidate = base / relative
            resolved = candidate.resolve(strict=True)
            if not resolved.is_relative_to(base) or _has_private_component(resolved.relative_to(base)) or resolved.suffix.lower() not in _ALLOWED_SUFFIXES or not resolved.is_file():
                raise ValueError
            if resolved.stat().st_size > _SOURCE_LIMIT:
                raise ValueError
            with resolved.open("rb") as source:
                content = source.read(_SOURCE_LIMIT + 1)
            if len(content) > _SOURCE_LIMIT:
                raise ValueError
            text = content.decode("utf-8")
        except (OSError, RuntimeError, ValueError, UnicodeError):
            display_path = requested if isinstance(requested, str) and not Path(requested).is_absolute() else "<path>"
            findings.append(_finding("scan-error", display_path, 0))
            continue

        test_path = _is_test_path(requested)
        for line_number, line in enumerate(text.splitlines(), 1):
            if not test_path and _SECRET_VALUE.search(line):
                findings.append(_finding("secret", requested, line_number))
            if not test_path and ".log(" in line and re.search(r"\bconsole\s*\.\s*log\s*\(", line):
                findings.append(_finding("console-log", requested, line_number))
            comment = _COMMENT.search(line)
            if not test_path and comment is not None:
                comment_text = line[comment.start() :]
                if _TODO.search(comment_text) and not _TICKET.search(comment_text):
                    findings.append(_finding("unticketed-todo", requested, line_number))
    return tuple(findings)


def _audit_json(output: str) -> object:
    return json.loads(output, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))


def parse_audit(returncode: int, output: str) -> StageResult:
    """Parse complete pip-audit JSON without retaining package diagnostics."""
    problems: list[str] = []
    count: int | None = None
    if isinstance(returncode, bool) or not isinstance(returncode, int):
        problems.append("Invalid audit process return code.")
    elif returncode != 0:
        problems.append("Dependency audit command failed.")
    try:
        if len(output.encode("utf-8")) > _AUDIT_LIMIT:
            raise ValueError
        data = _audit_json(output)
        if not isinstance(data, dict) or "skipped" in data:
            raise ValueError
        dependencies = data.get("dependencies")
        if not isinstance(dependencies, list) or not dependencies:
            raise ValueError
        total_vulnerabilities = 0
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                raise ValueError
            name, version, vulnerabilities = dependency.get("name"), dependency.get("version"), dependency.get("vulns")
            if not isinstance(name, str) or not name.strip() or not isinstance(version, str) or not version.strip() or not isinstance(vulnerabilities, list):
                raise ValueError
            if any(not isinstance(vulnerability, dict) or not isinstance(vulnerability.get("id"), str) or not vulnerability["id"] for vulnerability in vulnerabilities):
                raise ValueError
            total_vulnerabilities += len(vulnerabilities)
        count = total_vulnerabilities
        if count:
            problems.append("Dependency audit found vulnerabilities.")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        problems.append("Invalid or incomplete dependency audit evidence.")
    return StageResult("security", returncode if isinstance(returncode, int) and not isinstance(returncode, bool) else None, count=count, problems=tuple(problems))
