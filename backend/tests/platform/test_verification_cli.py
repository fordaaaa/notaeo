from __future__ import annotations

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Callable

import pytest
from fastapi.testclient import TestClient


def _module(monkeypatch: pytest.MonkeyPatch, root: Path, commands: dict[str, tuple[str, ...]]):
    from scripts import verify

    monkeypatch.setattr(verify, "REPO_ROOT", root)
    monkeypatch.setattr(verify, "COMMANDS", commands)
    return verify


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "backend" / "core").mkdir(parents=True)
    (root / "backend" / "api").mkdir()
    (root / "backend" / "scripts").mkdir()
    (root / "backend" / "core" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "backend" / "api" / "sample.py").write_text("VALUE = 2\n", encoding="utf-8")
    return root


def _executable(path: Path, body: str) -> tuple[str, ...]:
    path.write_text(f"#!{sys.executable}\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return (str(path),)


def _commands(tmp_path: Path, *, failing: str | None = None, delay: float = 0.0) -> dict[str, tuple[str, ...]]:
    """Create fixed synthetic commands; output artifacts through supplied argv."""
    result: dict[str, tuple[str, ...]] = {}
    for stage in ("build", "types", "lint", "tests", "coverage", "security", "diff", "touched", "untracked", "checkdiff"):
        prelude = f"import sys, json, pathlib, time\ntime.sleep({delay!r})\n"
        if stage == "types":
            body = prelude + "print(json.dumps({'summary': {'errorCount': 0, 'warningCount': 0}}))\n"
        elif stage == "lint":
            body = prelude + "print('[]')\n"
        elif stage == "tests":
            body = prelude + "\n".join([
                "for arg in sys.argv[1:]:",
                "    if arg.startswith('--junitxml='):",
                "        pathlib.Path(arg.split('=', 1)[1]).write_text('<testsuite tests=\"1\" failures=\"0\" errors=\"0\" skipped=\"0\"><testcase classname=\"x\" name=\"y\"/></testsuite>', encoding='utf-8')",
            ]) + "\n"
            result[stage] = _executable(tmp_path / f"{stage}.py", body) + ("--junitxml={junit}",)
            continue
        elif stage == "coverage":
            data = {"meta": {"branch_coverage": True}, "files": {"core/sample.py": {"summary": {"num_statements": 10, "covered_lines": 10, "missing_lines": 0, "num_branches": 2, "covered_branches": 2, "missing_branches": 0}}, "api/sample.py": {"summary": {"num_statements": 10, "covered_lines": 10, "missing_lines": 0, "num_branches": 2, "covered_branches": 2, "missing_branches": 0}}}, "totals": {"num_statements": 20, "covered_lines": 20, "missing_lines": 0, "num_branches": 4, "covered_branches": 4, "missing_branches": 0}}
            body = prelude + f"data = {data!r}\nfor i, arg in enumerate(sys.argv[1:]):\n    if arg == '-o': pathlib.Path(sys.argv[i+2]).write_text(json.dumps(data), encoding='utf-8')\n"
            result[stage] = _executable(tmp_path / f"{stage}.py", body) + ("-o", "{coverage}")
            continue
        elif stage == "security":
            body = prelude + "print(json.dumps({'dependencies': [{'name': 'synthetic-package', 'version': '1.0', 'vulns': []}]}))\n"
        else:
            body = prelude + "print('')\n"
        if stage == failing:
            body += "sys.exit(1)\n"
        result[stage] = _executable(tmp_path / f"{stage}.py", body)
    return result


def test_default_run_executes_fixed_stages_in_order_and_passes_unicode_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    commands = _commands(tmp_path)
    commands["build"] = commands["build"] + ("folder with space", "café", "semi;$(touch nope)")
    verify = _module(monkeypatch, root, commands)
    calls: list[tuple[tuple[str, ...], Path]] = []
    original: Callable[..., tuple[int | None, str]] = verify.run_command

    def record(argv: tuple[str, ...], cwd: Path, timeout: float) -> tuple[int | None, str]:
        calls.append((argv, cwd))
        return original(argv, cwd, timeout)

    monkeypatch.setattr(verify, "run_command", record)

    code = verify.main([])

    assert code == 0
    assert (root / "backend" / "build" / "verification").is_dir()
    expected = [commands[name] for name in ("build", "types", "lint", "tests", "coverage", "security", "diff", "touched", "untracked", "checkdiff")]
    for (actual, _), template in zip(calls, expected, strict=True):
        assert len(actual) == len(template)
        for value, part in zip(actual, template, strict=True):
            if "{junit}" in part:
                assert value.startswith("--junitxml=") and value.endswith(".xml")
            elif "{coverage}" in part:
                assert value.endswith(".json")
            else:
                assert value == part
    assert calls[0][0][-3:] == ("folder with space", "café", "semi;$(touch nope)")
    assert not (root / "nope").exists()


def test_build_failure_stops_later_stages_and_cannot_report_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    verify = _module(monkeypatch, _project(tmp_path), _commands(tmp_path, failing="build"))
    calls: list[tuple[str, ...]] = []
    original: Callable[..., tuple[int | None, str]] = verify.run_command

    def record(argv: tuple[str, ...], cwd: Path, timeout: float) -> tuple[int | None, str]:
        calls.append(argv)
        return original(argv, cwd, timeout)

    monkeypatch.setattr(verify, "run_command", record)
    assert verify.main([]) != 0
    assert len(calls) == 1


@pytest.mark.parametrize("bad_argv", [["--unknown"], ["--timeout", "nan"], ["--timeout", "0"], ["--timeout", "inf"]])
def test_cli_rejects_unknown_flags_and_invalid_timeouts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_argv: list[str],
) -> None:
    verify = _module(monkeypatch, _project(tmp_path), _commands(tmp_path))
    assert verify.main(bad_argv) != 0


def test_security_only_is_scoped_and_never_prints_overall_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    verify = _module(monkeypatch, _project(tmp_path), _commands(tmp_path))
    assert verify.main(["--security-only"]) == 0
    output = capsys.readouterr().out.upper()
    assert "SECURITY" in output
    assert "READY" not in output


def test_missing_tool_and_malformed_stage_output_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands = _commands(tmp_path)
    commands["types"] = (str(tmp_path / "does-not-exist"),)
    commands["lint"] = _executable(tmp_path / "lint.py", "print('not json')")
    verify = _module(monkeypatch, _project(tmp_path), commands)
    assert verify.main([]) != 0


def test_failing_nonbuild_stage_collects_following_evidence_but_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    verify = _module(monkeypatch, root, _commands(tmp_path, failing="lint"))
    assert verify.main([]) != 0
    assert len(list((root / "backend" / "build").glob("verification/*"))) == 0


def test_diagnostics_are_bounded_and_redact_secret_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    commands = _commands(tmp_path)
    commands["types"] = _executable(tmp_path / "types.py", "print('ghp_SUPERSECRET' + 'x' * 300000)")
    verify = _module(monkeypatch, _project(tmp_path), commands)
    assert verify.main([]) != 0
    output = capsys.readouterr().out
    assert "ghp_SUPERSECRET" not in output
    assert len(output) < 160_000


def test_timeout_reaps_only_owned_process_group(tmp_path: Path) -> None:
    from scripts.verify import run_command

    marker = tmp_path / "child.pid"
    child_code = "import os,time; open(%r,'w').write(str(os.getpid())); time.sleep(30)" % str(marker)
    parent_code = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',%r]); time.sleep(30)" % child_code
    code, output = run_command((sys.executable, "-c", parent_code), tmp_path, 0.2)
    assert code is None
    assert len(output.encode("utf-8")) <= 128 * 1024
    if marker.exists():
        child_pid = int(marker.read_text(encoding="utf-8"))
        time.sleep(0.05)
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)


def test_concurrent_runs_use_distinct_artifact_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    commands = _commands(tmp_path, delay=0.03)
    verify = _module(monkeypatch, root, commands)
    seen: list[str] = []
    lock = Lock()
    original: Callable[..., tuple[int | None, str]] = verify.run_command

    def record(argv: tuple[str, ...], cwd: Path, timeout: float) -> tuple[int | None, str]:
        with lock:
            seen.extend(argument for argument in argv if argument.endswith(".xml") or argument.endswith(".json"))
        return original(argv, cwd, timeout)

    monkeypatch.setattr(verify, "run_command", record)
    with ThreadPoolExecutor(max_workers=2) as executor:
        codes = list(executor.map(lambda _: verify.main([]), range(2)))
    assert codes == [0, 0]
    junit_paths = [Path(value.split("=", 1)[1]) for value in seen if ".xml" in value]
    coverage_paths = [Path(value) for value in seen if value.endswith(".json")]
    assert len(junit_paths) == 2 and junit_paths[0] != junit_paths[1]
    assert len(coverage_paths) == 2 and coverage_paths[0] != coverage_paths[1]
    assert not any(path.exists() for path in junit_paths + coverage_paths)


def test_account_boundary_uses_existing_temporary_sqlite_client(client: TestClient) -> None:
    notebooks = client.get("/api/notebooks")
    assert notebooks.status_code == 200
    assert isinstance(notebooks.json(), list)


def test_omitted_untouched_application_module_blocks_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    (root / "backend/core/unexecuted.py").write_text("VALUE = 3\n", encoding="utf-8")
    verify = _module(monkeypatch, root, _commands(tmp_path))
    assert verify.main([]) != 0


def test_security_only_scans_non_python_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    (root / "backend/scripts/debug.ts").write_text("console.log('debug')\n", encoding="utf-8")
    commands = _commands(tmp_path)
    commands["untracked"] = _executable(tmp_path / "untracked.py", "import sys; sys.stdout.write('backend/scripts/debug.ts\\0')")
    verify = _module(monkeypatch, root, commands)
    assert verify.main(["--security-only"]) != 0


def test_external_source_symlink_makes_scan_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf-8")
    (root / "backend/core/linked.py").symlink_to(outside)
    commands = _commands(tmp_path)
    commands["untracked"] = _executable(tmp_path / "untracked.py", "import sys; sys.stdout.write('backend/core/linked.py\\0')")
    verify = _module(monkeypatch, root, commands)
    assert verify.main(["--security-only"]) != 0


def test_untracked_file_count_is_in_diff_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path)
    (root / "notes.md").write_text("Synthetic documentation\n", encoding="utf-8")
    commands = _commands(tmp_path)
    commands["untracked"] = _executable(tmp_path / "untracked.py", "import sys; sys.stdout.write('notes.md\\0')")
    verify = _module(monkeypatch, root, commands)
    assert verify.main([]) == 0
    assert "Diff: (1 files)" in capsys.readouterr().out


def test_untracked_source_whitespace_is_checked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    (root / "notes.md").write_text("Trailing whitespace  \n", encoding="utf-8")
    commands = _commands(tmp_path)
    commands["untracked"] = _executable(tmp_path / "untracked.py", "import sys; sys.stdout.write('notes.md\\0')")
    verify = _module(monkeypatch, root, commands)
    assert verify.main([]) != 0


def test_truncated_git_inventory_cannot_produce_clean_security(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    commands = _commands(tmp_path)
    commands["untracked"] = _executable(tmp_path / "untracked.py", "import sys; sys.stdout.write('backend/core/a.py\\0' * 15000)")
    verify = _module(monkeypatch, root, commands)
    assert verify.main(["--security-only"]) != 0


def test_noisy_process_is_stopped_at_output_bound(tmp_path: Path) -> None:
    from scripts.verify import run_command

    marker = tmp_path / "finished"
    body = "import pathlib,sys; sys.stdout.buffer.write(b'x' * 500000); sys.stdout.flush(); pathlib.Path(sys.argv[1]).write_text('finished')"
    code, output = run_command((sys.executable, "-c", body, str(marker)), tmp_path, 5.0)
    assert code is None
    assert len(output.encode("utf-8")) <= 128 * 1024


def test_untracked_environment_file_blocks_diff_without_being_treated_as_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    (root / ".env").write_text("PRIVATE_SETTING=synthetic\n", encoding="utf-8")
    commands = _commands(tmp_path)
    commands["untracked"] = _executable(tmp_path / "untracked.py", "import sys; sys.stdout.write('.env\\0')")
    verify = _module(monkeypatch, root, commands)
    assert verify.main([]) != 0


def test_real_git_source_deletion_does_not_make_scan_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import verify

    root = _project(tmp_path)
    (root / ".gitignore").write_text("backend/build/\n", encoding="utf-8")
    obsolete = root / "backend/core/obsolete.py"
    obsolete.write_text("VALUE = 4\n", encoding="utf-8")
    for command in (
        ("git", "init"), ("git", "add", "."),
        ("git", "-c", "user.name=Verification Test", "-c", "user.email=verification@example.test",
         "-c", "commit.gpgsign=false", "commit", "-m", "fixture"),
    ):
        subprocess.run(command, cwd=root, check=True, capture_output=True)
    obsolete.unlink()
    commands = _commands(tmp_path)
    for name in ("diff", "touched", "untracked", "checkdiff"):
        commands[name] = verify.COMMANDS[name]
    verify = _module(monkeypatch, root, commands)
    assert verify.main([]) == 0


def test_malformed_git_inventory_blocks_scoped_security(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    commands = _commands(tmp_path)
    commands["untracked"] = _executable(tmp_path / "untracked.py", "print('not a NUL-delimited inventory')")
    verify = _module(monkeypatch, root, commands)
    assert verify.main(["--security-only"]) != 0


def test_non_utf8_command_output_is_incomplete_evidence(tmp_path: Path) -> None:
    from scripts.verify import run_command

    code, output = run_command((sys.executable, "-c", "import os; os.write(1, b'\\xff')"), tmp_path, 5.0)
    assert code is None
    assert "\ufffd" not in output


def test_external_source_directory_symlink_blocks_security(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    outside = tmp_path / "outside-package"
    outside.mkdir()
    (outside / "__init__.py").write_text("VALUE = 5\n", encoding="utf-8")
    (root / "backend/core/vendor").symlink_to(outside, target_is_directory=True)
    commands = _commands(tmp_path)
    commands["untracked"] = _executable(tmp_path / "untracked.py", "import sys; sys.stdout.write('backend/core/vendor\\0')")
    verify = _module(monkeypatch, root, commands)
    assert verify.main(["--security-only"]) != 0


@pytest.mark.parametrize("symlink", [False, True])
def test_untracked_special_files_fail_promptly(tmp_path: Path, symlink: bool) -> None:
    from scripts import verify

    root = _project(tmp_path)
    fifo = root / ("stream" if symlink else "notes.py")
    os.mkfifo(fifo)
    if symlink:
        (root / "notes.py").symlink_to(fifo)
    program = (
        "import sys; from pathlib import Path; from scripts import verify; "
        "raise SystemExit(0 if verify._check_untracked_whitespace(Path(sys.argv[1]), 'notes.py\\0') else 1)"
    )
    result = subprocess.run(
        (sys.executable, "-c", program, str(root)),
        cwd=Path(__file__).resolve().parents[2], capture_output=True, timeout=8,
    )
    assert result.returncode == 1
    assert not verify._check_untracked_whitespace(root, "notes.py\0")


@pytest.mark.parametrize("stage", ["diff", "touched", "untracked"])
def test_missing_git_inventory_reports_unknown_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stage: str,
) -> None:
    root = _project(tmp_path)
    commands = _commands(tmp_path)
    commands[stage] = (str(tmp_path / "missing-git"),)
    verify = _module(monkeypatch, root, commands)
    assert verify.main([]) != 0
    output = capsys.readouterr().out
    assert "Diff: (unknown files)" in output
    if stage != "diff":
        assert "Security: FAIL (unknown)" in output


def test_full_report_counts_source_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path)
    (root / "backend/scripts/debug.ts").write_text("console.log('debug')\n", encoding="utf-8")
    verify = _module(monkeypatch, root, _commands(tmp_path))
    assert verify.main([]) != 0
    assert "Security: FAIL (1)" in capsys.readouterr().out


@pytest.mark.parametrize("stage", ["tests", "coverage"])
def test_success_exit_without_new_artifact_does_not_pass_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stage: str,
) -> None:
    root = _project(tmp_path)
    commands = _commands(tmp_path)
    commands[stage] = _executable(tmp_path / f"{stage}.py", "print('no artifact emitted')")
    verify = _module(monkeypatch, root, commands)
    assert verify.main([]) != 0
    assert "Tests: FAIL" in capsys.readouterr().out


@pytest.mark.parametrize("size", [40, 300000])
def test_command_stderr_is_bounded_without_corrupting_structured_stdout(tmp_path: Path, size: int) -> None:
    from core.verification import parse_types
    from scripts.verify import run_command

    program = (
        f"import os; os.write(2, b'SYNTHETIC_PRIVATE_DIAGNOSTIC' + b'x' * {size}); "
        "os.write(1, b'{\"summary\":{\"errorCount\":0,\"warningCount\":0}}')"
    )
    code, output = run_command((sys.executable, "-c", program), tmp_path, 5)
    assert "SYNTHETIC_PRIVATE_DIAGNOSTIC" not in output
    if size > 128 * 1024:
        assert code is None
    else:
        assert code == 0
        assert not parse_types(code, output).problems
