"""Phase 1 verification-configuration regression tests (configuration only).

Configuration regression tests for the declared verification policy. This is
Phase 1 scope only: Python version, dev-only check tools, explicit stage
commands, type/lint scope, full branch coverage source and separate 80% floors.

There is no production verifier here. Helpers prefixed ``_scaffold_`` are TEST
SCAFFOLD assertion helpers for threshold/denominator fixtures, not runtime
validation and not the Phase 2 ``core/verification.py`` / ``scripts/verify.py``
gate. New policy schema lives under ``[tool.notaeo.verification]``; that table
is NEW configuration, not an existing codebase pattern.
"""

from __future__ import annotations

import math
import tomllib
from pathlib import Path
from typing import cast


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_pyproject() -> dict[str, object]:
    pyproject_path = _backend_dir() / "pyproject.toml"
    with pyproject_path.open("rb") as handle:
        data = cast(dict[str, object], tomllib.load(handle))
    return data


def _scaffold_table(value: object) -> dict[str, object]:
    """Narrow a parsed TOML table for the configuration tests."""
    assert isinstance(value, dict), "expected TOML table"
    assert all(isinstance(key, str) for key in value), "TOML keys must be strings"
    return cast(dict[str, object], value)


def _get_verification_policy(pyproject: dict[str, object]) -> dict[str, object]:
    tool = pyproject.get("tool")
    assert isinstance(tool, dict), "missing [tool] table in pyproject.toml"
    notaeo = tool.get("notaeo")
    assert isinstance(notaeo, dict), "missing [tool.notaeo] table (Phase 1 policy)"
    verification = notaeo.get("verification")
    assert isinstance(verification, dict), (
        "missing [tool.notaeo.verification] policy table (Phase 1 NEW config)"
    )
    return verification


def _get_pyright_config(pyproject: dict[str, object]) -> dict[str, object]:
    tool = pyproject.get("tool")
    assert isinstance(tool, dict), "missing [tool] table"
    pyright = tool.get("pyright")
    assert isinstance(pyright, dict), "missing [tool.pyright] configuration"
    return pyright


def _get_coverage_run(pyproject: dict[str, object]) -> dict[str, object]:
    tool = pyproject.get("tool")
    assert isinstance(tool, dict), "missing [tool] table"
    coverage = tool.get("coverage")
    assert isinstance(coverage, dict), "missing [tool.coverage] configuration"
    run = coverage.get("run")
    assert isinstance(run, dict), "missing [tool.coverage.run] configuration"
    return run


def _get_coverage_report(pyproject: dict[str, object]) -> dict[str, object]:
    tool = pyproject.get("tool")
    assert isinstance(tool, dict), "missing [tool] table"
    coverage = tool.get("coverage")
    assert isinstance(coverage, dict), "missing [tool.coverage] configuration"
    report = coverage.get("report")
    assert isinstance(report, dict), "missing [tool.coverage.report] configuration"
    return report


def _scaffold_meets_floor(value: object, floor: object) -> bool:
    """TEST SCAFFOLD: strict threshold check, not runtime validation.

    Returns True only for real int/float (excluding bool) with
    0 <= floor <= 100, 0 <= value <= 100 and value >= floor. All other
    inputs (bool, None, str, out-of-range, NaN via range check) fail closed.
    """
    if isinstance(value, bool) or isinstance(floor, bool):
        return False
    if not isinstance(value, (int, float)) or not isinstance(floor, (int, float)):
        return False
    value_f = float(value)
    floor_f = float(floor)
    if not (0.0 <= floor_f <= 100.0):
        return False
    if not (0.0 <= value_f <= 100.0):
        return False
    # NaN fails closed; math.isnan avoids self-comparison lint.
    if math.isnan(value_f) or math.isnan(floor_f):
        return False
    return value_f >= floor_f


def _scaffold_branch_pct(covered: object, total: object) -> float | None:
    """TEST SCAFFOLD: branch percentage, not runtime validation.

    Returns None for zero/invalid denominator (unknown, never PASS).
    """
    if isinstance(covered, bool) or isinstance(total, bool):
        return None
    if not isinstance(covered, (int, float)) or not isinstance(total, (int, float)):
        return None
    total_f = float(total)
    covered_f = float(covered)
    if math.isnan(total_f) or math.isnan(covered_f):
        return None
    if total_f <= 0.0:
        return None
    if covered_f < 0.0 or covered_f > total_f:
        return None
    return (covered_f / total_f) * 100.0


def _scaffold_meets_separate_floors(
    lines_pct: object,
    branches_pct: object,
    lines_floor: object,
    branches_floor: object,
) -> bool:
    """TEST SCAFFOLD: independent line+branch floors, not runtime validation."""
    return _scaffold_meets_floor(lines_pct, lines_floor) and _scaffold_meets_floor(
        branches_pct, branches_floor
    )


def test_python_requires_312_and_policy_pins_312() -> None:
    pyproject = _load_pyproject()
    requires_python = _scaffold_table(pyproject.get("project")).get("requires-python", "")
    assert "3.12" in str(requires_python), (
        f"requires-python must declare 3.12, got {requires_python!r}"
    )
    policy = _get_verification_policy(pyproject)
    assert policy.get("python_version") == "3.12", (
        "policy python_version must pin 3.12"
    )


def test_mandatory_dev_tools_are_dev_only() -> None:
    pyproject = _load_pyproject()
    groups = _scaffold_table(pyproject.get("dependency-groups"))
    dev = groups.get("dev", [])
    assert isinstance(dev, list), "missing [dependency-groups] dev list"
    dev_text = " ".join(str(item).lower() for item in dev)
    for tool_name in ("ruff", "pyright", "coverage", "pip-audit"):
        assert tool_name in dev_text, f"dev group must include {tool_name}"
    runtime_deps = _scaffold_table(pyproject.get("project")).get("dependencies", [])
    assert isinstance(runtime_deps, list), "runtime dependencies must be a list"
    runtime_text = " ".join(str(item).lower() for item in runtime_deps)
    for tool_name in ("ruff", "pyright", "coverage", "pip-audit"):
        assert tool_name not in runtime_text, (
            f"{tool_name} must stay dev-only, not a runtime dependency"
        )
    # No runtime paid service / node product introduced by this phase.
    for banned in ("openai", "anthropic", "boto", "node", "npm"):
        assert banned not in runtime_text, f"runtime must not add {banned}"


def test_verification_policy_table_exists() -> None:
    policy = _get_verification_policy(_load_pyproject())
    assert isinstance(policy.get("mandatory_dev_tools"), list)


def test_explicit_stage_commands_declared() -> None:
    policy = _get_verification_policy(_load_pyproject())
    commands = policy.get("commands")
    assert isinstance(commands, dict), "policy must declare [tool.notaeo.verification.commands]"
    required_stages = (
        "build",
        "types",
        "lint",
        "tests",
        "coverage_json",
        "coverage_report",
        "security",
        "diff",
    )
    for stage in required_stages:
        assert isinstance(commands.get(stage), str) and commands[stage].strip(), (
            f"stage {stage!r} must declare an explicit command string"
        )
    assert "build_macos_sidecar" in str(commands["build"]), "build must reuse sidecar script"
    assert "pyright" in str(commands["types"]), "types stage must run pyright"
    assert "ruff" in str(commands["lint"]) and "check" in str(commands["lint"]), (
        "lint stage must run ruff check"
    )
    assert "coverage" in str(commands["tests"]) and "--branch" in str(commands["tests"]), (
        "tests stage must run branch coverage"
    )
    assert "coverage" in str(commands["coverage_json"]), "coverage json artifact required"
    assert "pip-audit" in str(commands["security"]), "security stage must run pip-audit"
    assert "git diff" in str(commands["diff"]), "diff stage must run git diff"
    # Artifacts must avoid unignored repo-root writes: /tmp or ignored build/.
    artifact_text = str(commands["coverage_json"]) + str(policy.get("datadir", ""))
    assert ("/tmp" in artifact_text) or ("build/" in artifact_text), (
        "coverage artifacts/datadir must use /tmp or ignored build/ (no .gitignore change)"
    )


def test_pyright_standard_python312_with_venv() -> None:
    pyright = _get_pyright_config(_load_pyproject())
    assert pyright.get("pythonVersion") == "3.12", "pyright must set pythonVersion 3.12"
    assert pyright.get("typeCheckingMode") == "standard", (
        "pyright must use standard mode (not off/basic/strict override for green)"
    )
    assert isinstance(pyright.get("venv"), str) and str(pyright.get("venv")).strip(), (
        "pyright must declare venv"
    )
    assert isinstance(pyright.get("venvPath"), str) and str(
        pyright.get("venvPath")
    ).strip(), "pyright must declare venvPath"


def test_types_lint_scope_covers_core_api_scripts_and_config_test() -> None:
    pyproject = _load_pyproject()
    policy = _get_verification_policy(pyproject)
    for key in ("types_scope", "lint_scope"):
        scope = policy.get(key)
        assert isinstance(scope, list) and scope, f"policy {key} must be a non-empty list"
        scope_text = " ".join(str(item) for item in scope)
        for required in (
            "core",
            "api",
            "scripts",
            "tests/platform/test_verification_configuration.py",
        ):
            assert required in scope_text, f"policy {key} must include {required}"
    pyright = _get_pyright_config(pyproject)
    include = pyright.get("include", [])
    assert isinstance(include, list) and include, "pyright include must be explicit"
    include_text = " ".join(str(item) for item in include)
    for required in ("core", "api", "scripts"):
        assert required in include_text, f"pyright include must cover {required}"


def test_types_lint_have_no_suppressions_or_narrowing() -> None:
    pyproject = _load_pyproject()
    pyright = _get_pyright_config(pyproject)
    for forbidden in (
        "exclude",
        "ignore",
        "disableLanguageServices",
        "disableTaggedHints",
    ):
        assert forbidden not in pyright, f"pyright must not set {forbidden} to pass"
    assert pyright.get("typeCheckingMode") != "off", "pyright must not be turned off"
    # No untyped-code bypass: strict-false overrides that silence diagnostics fail policy.
    for key, value in pyright.items():
        if key.startswith("report") and isinstance(value, bool):
            # Policy forbids turning diagnostics off to get green; defaults stay on.
            assert value is not False, (
                f"pyright {key}=false disables diagnostics for green"
            )
    tool = _scaffold_table(pyproject.get("tool"))
    ruff = tool.get("ruff", {})
    if isinstance(ruff, dict) and ruff:
        assert "exclude" not in ruff, "ruff must not exclude app files for green"
        ignore = ruff.get("ignore", [])
        if isinstance(ignore, list):
            ignore_text = " ".join(str(item) for item in ignore)
            for rule in ("E4", "E7", "E9", "F"):
                assert rule not in ignore_text, f"ruff must not ignore {rule} baseline"


def test_coverage_branch_full_source_core_api() -> None:
    pyproject = _load_pyproject()
    policy = _get_verification_policy(pyproject)
    assert policy.get("coverage_branch") is True, "policy coverage_branch must be true"
    source = policy.get("coverage_source")
    assert isinstance(source, list), "policy coverage_source must be a list"
    assert "core" in source and "api" in source, "policy source must be core+api"
    run = _get_coverage_run(pyproject)
    assert run.get("branch") is True, "[tool.coverage.run] branch must be true"
    run_source = run.get("source", [])
    assert isinstance(run_source, list), "[tool.coverage.run] source must be a list"
    assert "core" in run_source and "api" in run_source, (
        "[tool.coverage.run] source must include core and api"
    )


def test_coverage_includes_unexecuted_files_no_omit_or_pragma_removal() -> None:
    run = _get_coverage_run(_load_pyproject())
    assert "omit" not in run or not run.get("omit"), (
        "[tool.coverage.run] must not omit files to hide uncovered app code"
    )
    tool = _scaffold_table(_load_pyproject().get("tool"))
    coverage = tool.get("coverage", {})
    assert isinstance(coverage, dict)
    report = coverage.get("report", {})
    if isinstance(report, dict):
        assert "omit" not in report or not report.get("omit"), (
            "[tool.coverage.report] must not omit files"
        )
        # Removing default pragma handling to inflate scores fails policy.
        if "exclude_also" in report:
            assert not report["exclude_also"], "must not extend exclusions for green"
    # Declared source must be full core+api, not a narrowed single-file glob.
    assert run.get("source") != ["core"], "source must not narrow to core only"
    assert run.get("source") != ["api"], "source must not narrow to api only"


def test_coverage_floors_lines_branches_combined_are_80() -> None:
    policy = _get_verification_policy(_load_pyproject())
    assert policy.get("lines_floor") == 80, "policy lines_floor must be 80"
    assert policy.get("branches_floor") == 80, "policy branches_floor must be 80"
    assert policy.get("combined_floor") == 80, "policy combined_floor must be 80"
    report = _get_coverage_report(_load_pyproject())
    # Combined `fail_under` alone does not prove separate floors; both must exist.
    assert report.get("fail_under") == 80, "[tool.coverage.report] fail_under must be 80"
    assert policy.get("lines_floor") == 80 and policy.get("branches_floor") == 80, (
        "independent line+branch floors required alongside combined fail_under"
    )


def test_threshold_boundaries_79_99_80_100(tmp_path: Path) -> None:
    policy = _get_verification_policy(_load_pyproject())
    lines_floor = policy.get("lines_floor")
    assert lines_floor == 80
    assert _scaffold_meets_floor(79.99, lines_floor) is False, "79.99 must fail an 80 floor"
    assert _scaffold_meets_floor(80, lines_floor) is True, "80 must pass an 80 floor"
    assert _scaffold_meets_floor(100, lines_floor) is True, "100 must pass an 80 floor"
    assert _scaffold_meets_floor(80.0, 80) is True
    # Temporary fixture form: write boundary values to a temp file and re-check.
    fixture = tmp_path / "thresholds.txt"
    fixture.write_text("79.99\n80\n100\n")
    values = [float(line) for line in fixture.read_text().splitlines()]
    assert [_scaffold_meets_floor(value, 80) for value in values] == [False, True, True]


def test_threshold_rejects_invalid_bool_null_outofrange_empty() -> None:
    assert _scaffold_meets_floor(True, 80) is False, "bool must not count as 80"
    assert _scaffold_meets_floor(False, 80) is False
    assert _scaffold_meets_floor(None, 80) is False, "null must fail closed"
    assert _scaffold_meets_floor("80", 80) is False, "string must fail closed"
    assert _scaffold_meets_floor(80, True) is False, "bool floor is invalid"
    assert _scaffold_meets_floor(80, None) is False, "null floor is invalid"
    assert _scaffold_meets_floor(-0.5, 80) is False, "negative percent is invalid"
    assert _scaffold_meets_floor(101, 80) is False, ">100 percent is invalid"
    assert _scaffold_meets_floor(80, 101) is False, ">100 floor is invalid"
    assert _scaffold_meets_floor(80, -1) is False, "negative floor is invalid"
    assert _scaffold_meets_floor(float("nan"), 80) is False, "NaN must fail closed"


def test_zero_branch_denominator_is_unknown_not_pass(tmp_path: Path) -> None:
    assert _scaffold_branch_pct(0, 0) is None, "zero branches is unknown, not 100%"
    assert _scaffold_branch_pct(5, 0) is None
    assert _scaffold_branch_pct(0, 10) == 0.0
    assert _scaffold_branch_pct(8, 10) == 80.0
    fixture = tmp_path / "branches.json"
    fixture.write_text('{"covered": 0, "total": 0}')
    assert _scaffold_branch_pct(0, 0) is None, "empty denominator fixture must not PASS"
    assert _scaffold_meets_floor(_scaffold_branch_pct(0, 0), 80) is False


def test_combined_score_does_not_enforce_separate_floors() -> None:
    # Lines 100 + branches 60 averages to combined 80, but branch floor 80 fails.
    assert _scaffold_meets_separate_floors(100, 60, 80, 80) is False, (
        "combined 80 must not mask a 60 branch score"
    )
    assert _scaffold_meets_separate_floors(60, 100, 80, 80) is False
    assert _scaffold_meets_separate_floors(80, 80, 80, 80) is True
    assert _scaffold_meets_separate_floors(100, 100, 80, 80) is True
    assert _scaffold_meets_separate_floors(79.99, 100, 80, 80) is False
    assert _scaffold_meets_separate_floors(None, 80, 80, 80) is False
    assert _scaffold_meets_separate_floors(True, 80, 80, 80) is False


def test_exclusion_fixture_fails_full_source_policy(tmp_path: Path) -> None:
    policy = _get_verification_policy(_load_pyproject())
    declared = policy.get("coverage_source", [])
    assert isinstance(declared, list), "coverage_source must be a list"
    assert "core" in declared and "api" in declared
    narrowed = tmp_path / "narrowed.toml"
    narrowed.write_text('source = ["core"]\n')
    narrowed_text = narrowed.read_text()
    assert "api" not in narrowed_text, "narrowed fixture must drop api"
    assert declared != ["core"], "narrowed core-only scope fails full-source policy"
    excluded = tmp_path / "excluded.toml"
    excluded.write_text('omit = ["core/store.py"]\n')
    assert "omit" in excluded.read_text(), "exclusion fixture must show omit"
    run = _get_coverage_run(_load_pyproject())
    assert "omit" not in run or not run.get("omit"), "real config must not omit app files"


def test_touched_policy_declares_future_paths_without_claiming_existence() -> None:
    policy = _get_verification_policy(_load_pyproject())
    touched = policy.get("touched", {})
    assert isinstance(touched, dict), "policy must declare [tool.notaeo.verification.touched]"
    future_paths = touched.get("future_paths", [])
    assert isinstance(future_paths, list) and future_paths, "future_paths must be listed"
    future_text = " ".join(str(item) for item in future_paths)
    for expected in (
        "core/verification.py",
        "scripts/verify.py",
        "tests/core/test_verification.py",
        "tests/platform/test_verification_cli.py",
    ):
        assert expected in future_text, f"touched policy must declare {expected}"
    # This is a scope declaration, never evidence of implementation. Do not
    # make future valid phases fail by requiring their files to stay absent.
    assert touched.get("scope_declaration_only") is True


def test_policy_datadir_is_ignored_location() -> None:
    policy = _get_verification_policy(_load_pyproject())
    datadir = str(policy.get("datadir", ""))
    assert datadir.strip(), "policy datadir must be declared"
    assert ("build/" in datadir) or ("/tmp" in datadir), (
        "datadir must be ignored build/ or /tmp (no Phase 3 .gitignore change)"
    )


def test_coverage_database_uses_declared_ignored_datadir() -> None:
    """Coverage's real setting, not only metadata, must keep artifacts ignored."""
    pyproject = _load_pyproject()
    policy = _get_verification_policy(pyproject)
    run = _get_coverage_run(pyproject)
    assert run.get("data_file") == f"{policy['datadir']}/.coverage"


def test_ruff_python_and_default_rule_families_are_explicit() -> None:
    pyproject = _load_pyproject()
    tool = pyproject["tool"]
    assert isinstance(tool, dict)
    ruff = tool.get("ruff")
    assert isinstance(ruff, dict)
    assert ruff.get("target-version") == "py312"
    lint = ruff.get("lint")
    assert isinstance(lint, dict)
    assert lint.get("select") == ["E4", "E7", "E9", "F"]
    assert not lint.get("ignore")
    assert not lint.get("per-file-ignores")


def test_command_workdirs_are_explicit() -> None:
    policy = _get_verification_policy(_load_pyproject())
    assert policy.get("build_workdir") == "repository"
    assert policy.get("checks_workdir") == "backend"


def test_locked_urllib3_excludes_known_vulnerable_releases() -> None:
    """Keep the resolved HTTP dependency beyond the audited vulnerable range."""
    from packaging.version import Version

    lock = tomllib.loads((_backend_dir() / "uv.lock").read_text())
    packages = lock["package"]
    urllib3_versions = [item["version"] for item in packages if item["name"] == "urllib3"]
    assert urllib3_versions, "expected the transitive urllib3 dependency in the lock"
    assert all(Version(value) >= Version("2.8.0") for value in urllib3_versions)
