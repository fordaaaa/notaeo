from pathlib import Path

import pytest

from core.verification import StageResult
from core.verification_security import parse_audit, scan_source


def _write(root: Path, name: str, text: str) -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def test_scan_reports_only_redacted_finding_metadata(tmp_path: Path) -> None:
    secret = "sk-live-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    _write(tmp_path, "src/app.py", f'API_TOKEN = "{secret}"\n')

    findings = scan_source(tmp_path, ("src/app.py",))

    assert any(f.get("rule") == "secret" and f.get("path") == "src/app.py" and f.get("line") == 1 for f in findings)
    assert secret not in repr(findings)


def test_scan_ignores_nonsecret_context_and_test_fixtures(tmp_path: Path) -> None:
    _write(tmp_path, "src/config.py", 'token = os.environ["API_KEY"]\nPUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI"\nchecksum = "sha256:0123456789abcdef"\n')
    _write(tmp_path, "tests/test_credentials.py", 'secret = "sk-live-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"\n')

    assert scan_source(tmp_path, ("src/config.py", "tests/test_credentials.py")) == ()


def test_scan_reports_console_log_and_unticketed_todo(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.ts", "console.log('debug')\n// TODO remove debug\n// FIXME ABC-123 follow-up\n")

    findings = scan_source(tmp_path, ("src/app.ts",))

    assert {(f.get("rule"), f.get("line")) for f in findings} >= {
        ("console-log", 1),
        ("unticketed-todo", 2),
    }
    assert not any(f.get("rule") == "unticketed-todo" and f.get("line") == 3 for f in findings)


@pytest.mark.parametrize("requested", ["/etc/passwd", "../outside.py", ".env", "data/app.db", "db.sqlite"])
def test_scan_rejected_paths_fail_closed(tmp_path: Path, requested: str) -> None:
    findings = scan_source(tmp_path, (requested,))

    assert any(f.get("rule") == "scan-error" for f in findings)


def test_scan_rejects_external_symlink_and_empty_paths_have_no_candidates(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.py"
    outside.write_text("password = 'example'\n", encoding="utf-8")
    (tmp_path / "linked.py").symlink_to(outside)

    assert any(f.get("rule") == "scan-error" for f in scan_source(tmp_path, ("linked.py",)))
    assert scan_source(tmp_path, ()) == ()


@pytest.mark.parametrize("name,text", [("missing.py", None), ("large.py", "x" * (2 * 1024 * 1024 + 1))])
def test_scan_missing_or_oversize_source_is_an_error(tmp_path: Path, name: str, text: str | None) -> None:
    if text is not None:
        _write(tmp_path, name, text)

    assert any(f.get("rule") == "scan-error" for f in scan_source(tmp_path, (name,)))


def test_parse_audit_accepts_complete_clean_pip_audit_schema() -> None:
    output = '{"dependencies":[{"name":"demo","version":"1.0","vulns":[]}]}'

    result = parse_audit(0, output)

    assert isinstance(result, StageResult)
    assert result.stage == "security"
    assert result.count == 0
    assert not result.problems


@pytest.mark.parametrize(
    "returncode,output",
    [
        (0, '{"dependencies":[{"name":"demo","version":"1.0","vulns":[{"id":"CVE-2026-1234"}]}]}'),
        (1, '{"dependencies":[]}'),
        (0, ""),
        (0, '{"dependencies":[{"name":"demo","version":"1.0"}]}'),
        (0, '{"dependencies":[{"name":"demo","version":"1.0","vulns":[]}],"skipped":[{"name":"other"}]}'),
        (0, '{"dependencies":[{"name":true,"version":"1.0","vulns":[]}]}'),
        (0, '{"dependencies":[{"name":"demo","version":"1.0","vulns":"none"}]}'),
        (0, "not json"),
    ],
)
def test_parse_audit_incomplete_or_unsafe_evidence_fails_closed(returncode: int, output: str) -> None:
    result = parse_audit(returncode, output)

    assert result.stage == "security"
    assert result.problems
    assert "CVE-2026-1234" not in repr(result)


@pytest.mark.parametrize("name", ["data/private.py", ".env.local.py"])
def test_scan_rejects_data_directory_even_with_code_extension(tmp_path: Path, name: str) -> None:
    _write(tmp_path, name, "VALUE = 1\n")
    assert any(item["rule"] == "scan-error" for item in scan_source(tmp_path, (name,)))


def test_scan_detects_standard_sk_prefix_without_a_provider_label(tmp_path: Path) -> None:
    value = "sk-" + "syntheticcredential" * 3
    _write(tmp_path, "src/app.py", f'client = "{value}"\n')
    findings = scan_source(tmp_path, ("src/app.py",))
    assert any(item["rule"] == "secret" for item in findings)
    assert value not in repr(findings)
