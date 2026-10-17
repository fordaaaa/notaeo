"""Run the repository's fixed, fail-closed verification workflow."""

from __future__ import annotations

import argparse
import json
import math
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import NoReturn, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.verification import STAGES, StageResult, format_report, is_ready, parse_lint, parse_tests, parse_types
from core.verification_security import parse_audit, scan_source

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS: dict[str, tuple[str, ...]] = {
    "build": ("sh", "backend/scripts/build_macos_sidecar.sh"),
    "types": ("uv", "run", "pyright", "--outputjson", "core", "api", "scripts", "tests/core/test_verification.py", "tests/core/test_verification_security.py", "tests/platform/test_verification_cli.py", "tests/platform/test_verification_configuration.py", "tests/api/test_classes.py"),
    "lint": ("uv", "run", "ruff", "check", "--output-format=json", "core", "api", "scripts", "tests/core/test_verification.py", "tests/core/test_verification_security.py", "tests/platform/test_verification_cli.py", "tests/platform/test_verification_configuration.py", "tests/api/test_classes.py"),
    "tests": ("uv", "run", "coverage", "run", "--data-file={data}", "--branch", "--source=core,api,scripts", "-m", "pytest", "--junitxml={junit}"),
    "coverage": ("uv", "run", "coverage", "json", "--data-file={data}", "-o", "{coverage}"),
    "security": ("uv", "run", "pip-audit", "--local", "--strict", "--format", "json"),
    "diff": ("git", "diff", "--name-only", "-z", "HEAD", "--"),
    "touched": ("git", "diff", "--name-only", "--diff-filter=ACMR", "-z", "HEAD", "--"),
    "untracked": ("git", "ls-files", "--others", "--exclude-standard", "-z"),
    "checkdiff": ("git", "diff", "--check", "HEAD", "--"),
}
_MAX_OUTPUT = 128 * 1024
_CODE_SUFFIXES = {".py", ".swift", ".cs", ".js", ".ts", ".tsx", ".jsx"}
_TEXT_SUFFIXES = _CODE_SUFFIXES | {".md", ".toml", ".yaml", ".yml", ".sh", ".json", ".txt", ".lock"}
_PRIVATE_PARTS = {"data", "db", "database", ".env", ".cache"}


def run_command(argv: tuple[str, ...], cwd: Path, timeout: float) -> tuple[int | None, str]:
    """Execute one argv vector without a shell and bound captured output."""
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except (OSError, ValueError):
        return None, "Command could not be started."
    if process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        return None, "Command output could not be captured."
    output = bytearray()
    captured_bytes = 0
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, data="stdout")
            selector.register(process.stderr, selectors.EVENT_READ, data="stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    captured_bytes += len(chunk)
                    if captured_bytes > _MAX_OUTPUT:
                        raise OverflowError
                    if key.data == "stdout":
                        output.extend(chunk)
        returncode = process.wait(timeout=max(0.001, deadline - time.monotonic()))
    except OverflowError:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        return None, "Command output exceeded the diagnostic limit."
    except (TimeoutError, subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        return None, "Command timed out or was interrupted."
    finally:
        process.stdout.close()
        process.stderr.close()
    try:
        return returncode, output.decode("utf-8")
    except UnicodeError:
        return None, "Command output encoding is invalid."


def _argv(name: str, junit: Path | None = None, coverage: Path | None = None, data: Path | None = None) -> tuple[str, ...]:
    replacements = {"{junit}": str(junit or ""), "{coverage}": str(coverage or ""), "{data}": str(data or "")}
    return tuple(next((part.replace(token, value) for token, value in replacements.items() if token in part), part) for part in COMMANDS[name])


def _safe_python_paths(texts: Sequence[str], root: Path) -> tuple[str, ...]:
    found: set[str] = set()
    for text in texts:
        for value in _nul_paths(text):
            normalized = value.replace("\\", "/")
            if not normalized.startswith("backend/"):
                continue
            relative = normalized[len("backend/"):]
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or path.suffix != ".py":
                continue
            if (root / "backend" / path).is_file():
                found.add(relative)
    return tuple(sorted(found))


def _security_only(root: Path, timeout: float) -> int:
    code, output = run_command(_argv("security"), root / "backend", timeout)
    audit = parse_audit(-1 if code is None else code, output)
    paths_code, paths_output = run_command(_argv("touched"), root, timeout)
    untracked_code, untracked_output = run_command(_argv("untracked"), root, timeout)
    if not _complete_inventory(paths_code, paths_output) or not _complete_inventory(untracked_code, untracked_output):
        print("SECURITY: FAIL. Source inventory unavailable.")
        return 1
    paths = _security_source_paths(root, paths_output, untracked_output)
    findings = scan_source(root / "backend", paths)
    issues = list(audit.problems)
    if any(item.get("rule") == "scan-error" for item in findings):
        issues.append("Source scan could not inspect every requested file.")
    if any(item.get("rule") != "scan-error" for item in findings):
        issues.append("Source scan found a security issue.")
    if issues:
        print("SECURITY: FAIL. " + " ".join(issues))
        return 1
    print("SECURITY: PASS.")
    return 0


def _main(argv: list[str] | None = None) -> int:
    class SafeArgumentParser(argparse.ArgumentParser):
        def error(self, message: str) -> NoReturn:
            del message
            print("Invalid arguments.", file=sys.stderr)
            raise SystemExit(2)

    parser = SafeArgumentParser(description="Run fixed repository verification checks.")
    parser.add_argument("--security-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=900.0)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    timeout = args.timeout
    if not math.isfinite(timeout) or timeout <= 0:
        print("Invalid timeout.")
        return 2
    root = REPO_ROOT.resolve()
    if args.security_only:
        return _security_only(root, timeout)

    base = root / "backend" / "build" / "verification"
    base.mkdir(parents=True, exist_ok=True)
    results: dict[str, StageResult] = {}
    with tempfile.TemporaryDirectory(prefix="run-", dir=base) as work:
        folder = Path(work)
        junit, coverage, data = folder / "results.xml", folder / "coverage.json", folder / ".coverage"

        def run(name: str, cwd: Path) -> tuple[int | None, str]:
            return run_command(_argv(name, junit, coverage, data), cwd, timeout)

        code, output = run("build", root)
        results["build"] = StageResult("build", code, problems=() if code == 0 else ("Build command failed or could not run.",))
        if code != 0:
            report = format_report(tuple(results.get(stage, StageResult(stage, None, problems=("Evidence was not collected.",))) for stage in STAGES))
            print(report)
            return 1

        code, output = run("types", root / "backend")
        results["types"] = parse_types(-1 if code is None else code, output)
        code, output = run("lint", root / "backend")
        results["lint"] = parse_lint(-1 if code is None else code, output)

        code, output = run("tests", root / "backend")
        test_code = code
        coverage_code, coverage_output = run("coverage", root / "backend")
        try:
            junit_output = _read_evidence(junit)
            coverage_evidence = _read_evidence(coverage) if coverage_code == 0 else ""
        except (OSError, UnicodeError, ValueError):
            junit_output, coverage_evidence = "", ""
        audit_code, audit_output = run("security", root / "backend")
        audit = parse_audit(-1 if audit_code is None else audit_code, audit_output)
        diff_code, diff_output = run("diff", root)
        touched_code, touched_output = run("touched", root)
        untracked_code, untracked_output = run("untracked", root)
        check_code, check_output = run("checkdiff", root)
        if not _complete_inventory(diff_code, diff_output):
            diff_code = None
        if not _complete_inventory(touched_code, touched_output):
            touched_code = None
        if not _complete_inventory(untracked_code, untracked_output):
            untracked_code = None
        touched = tuple(path for path in _safe_python_paths((touched_output, untracked_output), root) if path.startswith(("core/", "api/", "scripts/"))) if touched_code == 0 and untracked_code == 0 else ()
        results["tests"] = parse_tests(-1 if test_code is None or coverage_code != 0 else test_code, junit_output, coverage_evidence, touched)
        if not _coverage_includes_all_application_files(root, coverage_evidence):
            prior = results["tests"]
            results["tests"] = StageResult(prior.stage, prior.returncode, prior.count, prior.passed, prior.total, prior.coverage, prior.problems + ("Coverage omits an on-disk core or API Python module.",))
        if touched_code != 0 or untracked_code != 0:
            prior = results["tests"]
            results["tests"] = StageResult(prior.stage, prior.returncode, prior.count, prior.passed, prior.total, prior.coverage, prior.problems + ("Git source inventory unavailable.",))

        security_problems = list(audit.problems)
        security_count = audit.count
        if touched_code != 0 or untracked_code != 0:
            security_problems.append("Source inventory unavailable.")
            security_count = None
        else:
            source_paths = _security_source_paths(root, touched_output, untracked_output)
            findings = scan_source(root / "backend", source_paths)
            if any(item.get("rule") == "scan-error" for item in findings):
                security_problems.append("Source scan could not inspect every requested file.")
                security_count = None
            elif security_count is not None:
                security_count += len(findings)
            if any(item.get("rule") != "scan-error" for item in findings):
                security_problems.append("Source scan found a security issue.")
        results["security"] = StageResult("security", audit_code, count=security_count, problems=tuple(security_problems))
        if diff_code == 0 and touched_code == 0 and untracked_code == 0:
            changed_paths = set(_nul_paths(diff_output))
            changed_paths.update(_nul_paths(untracked_output))
            count = len(changed_paths)
        else:
            count = None
        untracked_whitespace = _check_untracked_whitespace(root, untracked_output) if untracked_code == 0 else False
        problems = (() if diff_code == 0 and touched_code == 0 and untracked_code == 0 else ("Git diff inventory unavailable.",)) + (() if check_code == 0 and not check_output.strip() and untracked_whitespace else ("Whitespace check failed or could not run.",))
        results["diff"] = StageResult("diff", 0 if diff_code == 0 and check_code == 0 else 1, count=count, problems=problems)

        report = format_report(tuple(results.get(stage, StageResult(stage, None, problems=("Evidence was not collected.",))) for stage in STAGES))
        print(report)
        return 0 if is_ready(tuple(results.get(stage, StageResult(stage, None)) for stage in STAGES)) else 1


def _security_source_paths(root: Path, changed: str, untracked: str) -> tuple[str, ...]:
    paths: set[str] = set()
    for value in (*_nul_paths(changed), *_nul_paths(untracked)):
        normalized = value.replace("\\", "/")
        if not normalized.startswith("backend/"):
            continue
        relative = normalized[len("backend/"):]
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.suffix not in _CODE_SUFFIXES or not path.parts or path.parts[0] not in {"core", "api", "scripts"}:
            continue
        paths.add(relative)
    for area in ("core", "api", "scripts"):
        source_root = root / "backend" / area
        if source_root.is_symlink():
            paths.add(area)
            continue
        for candidate in source_root.rglob("*"):
            if candidate.is_symlink() or candidate.suffix in _CODE_SUFFIXES:
                paths.add(candidate.relative_to(root / "backend").as_posix())
    return tuple(sorted(paths))


def _read_evidence(path: Path) -> str:
    with path.open("rb") as evidence:
        data = evidence.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("Evidence exceeds size limit.")
    return data.decode("utf-8")


def _coverage_includes_all_application_files(root: Path, evidence: str) -> bool:
    try:
        parsed = json.loads(evidence)
        files = parsed["files"]
        if not isinstance(files, dict):
            return False
        observed = {str(name).replace("\\", "/") for name in files}
    except (json.JSONDecodeError, KeyError, TypeError):
        return False
    expected = {
        path.relative_to(root / "backend").as_posix()
        for area in ("core", "api")
        for path in (root / "backend" / area).rglob("*.py")
        if path.is_file()
    }
    return bool(expected) and expected.issubset(observed)


def _check_untracked_whitespace(root: Path, output: str) -> bool:
    for value in _nul_paths(output):
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or _private_path(path):
            return False
        target = root / path
        try:
            relative = target.resolve().relative_to(root.resolve())
            if _private_path(relative) or not target.is_file():
                return False
            if path.suffix not in _TEXT_SUFFIXES and path.name not in {".gitignore", "Dockerfile"}:
                continue
            with target.open("rb") as source:
                content = source.read(2 * 1024 * 1024 + 1)
        except (OSError, ValueError):
            return False
        if len(content) > 2 * 1024 * 1024:
            return False
        if any(line.endswith((b" ", b"\t")) for line in content.splitlines()):
            return False
    return True


def _private_path(path: Path) -> bool:
    return any(part.lower() in _PRIVATE_PARTS or part.lower().startswith(".env.") or
               part.lower().endswith((".db", ".sqlite", ".sqlite3")) for part in path.parts)


def _complete_inventory(code: int | None, output: str) -> bool:
    if not isinstance(code, int) or isinstance(code, bool) or code != 0:
        return False
    if output in ("", "\n"):
        return True
    if not output.endswith("\0"):
        return False
    return all(value and not Path(value).is_absolute() and ".." not in Path(value).parts
               for value in output[:-1].split("\0"))


def _nul_paths(output: str) -> tuple[str, ...]:
    if output in ("", "\n"):
        return ()
    values = output.split("\0")
    if values[-1] == "":
        values.pop()
    return tuple(values)


def main(argv: list[str] | None = None) -> int:
    return _main(argv)


if __name__ == "__main__":
    sys.exit(main())
