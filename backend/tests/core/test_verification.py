from __future__ import annotations

from collections.abc import Callable
import json
from dataclasses import FrozenInstanceError

import pytest

from core.verification import StageResult, format_report, is_ready, parse_lint, parse_tests, parse_types


def test_stage_result_is_frozen_and_keeps_unknown_values() -> None:
    result = StageResult("types", None, count=None, problems=())
    assert result.returncode is None
    assert result.count is None
    try:
        setattr(result, "count", 0)
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("StageResult must be immutable")


def test_parse_types_counts_errors_and_warnings_and_fails_nonzero() -> None:
    output = json.dumps({"summary": {"errorCount": 2, "warningCount": 1}})
    result = parse_types(1, output)
    assert result.stage == "types"
    assert result.count == 3
    assert result.problems


def test_parse_types_rejects_malformed_missing_boolean_and_negative_counts() -> None:
    for output in ("{", "{}", json.dumps({"summary": {"errorCount": True, "warningCount": 0}}),
                   json.dumps({"summary": {"errorCount": -1, "warningCount": 0}})):
        result = parse_types(0, output)
        assert result.problems
        assert result.count is None


def test_parse_lint_counts_valid_diagnostics_and_requires_zero_exit() -> None:
    output = json.dumps([{"code": "F401", "message": "unused", "location": {"row": 2, "column": 1}}])
    result = parse_lint(0, output)
    assert result.count == 1
    assert not result.problems
    assert parse_lint(1, "[]").problems


def test_parse_lint_rejects_invalid_json_or_diagnostic_entries() -> None:
    for output in ("not json", "[null]", "[{}]"):
        result = parse_lint(0, output)
        assert result.problems
        assert result.count is None


def _coverage(*, lines: int = 100, covered_lines: int = 90, branches: int = 20,
              covered_branches: int = 18, per_file: tuple[tuple[str, int, int], ...] | None = None,
              branch_coverage: bool = True) -> str:
    files: dict[str, object] = {}
    entries = per_file or (("core/a.py", lines, covered_lines), ("api/b.py", lines, covered_lines))
    for name, file_lines, file_covered_lines in entries:
        files[name] = {
            "summary": {
                "num_statements": file_lines,
                "covered_lines": file_covered_lines,
                "num_branches": branches,
                "covered_branches": covered_branches,
            }
        }
    return json.dumps({
        "meta": {"branch_coverage": branch_coverage},
        "totals": {
            "num_statements": lines * 2,
            "covered_lines": covered_lines * 2,
            "num_branches": branches * 2,
            "covered_branches": covered_branches * 2,
        },
        "files": files,
    })


def _junit(*, tests: int = 10, failures: int = 0, errors: int = 0, skipped: int = 0) -> str:
    cases = "".join(
        "<testcase><skipped /></testcase>" if index < skipped else
        "<testcase><failure /></testcase>" if index < skipped + failures else
        "<testcase><error /></testcase>" if index < skipped + failures + errors else
        "<testcase />"
        for index in range(tests)
    )
    return f'<testsuite tests="{tests}" failures="{failures}" errors="{errors}" skipped="{skipped}">{cases}</testsuite>'


def test_parse_tests_validates_counts_and_full_plus_touched_coverage() -> None:
    result = parse_tests(0, _junit(), _coverage(), touched=("core/a.py",))
    assert result.stage == "tests"
    assert result.passed == 10
    assert result.total == 10
    assert result.coverage == 90.0
    assert not result.problems


def test_parse_tests_skips_are_not_passes_and_nonzero_or_failure_fails() -> None:
    skipped = parse_tests(0, _junit(tests=3, skipped=1), _coverage())
    assert skipped.passed == 2
    assert skipped.total == 3
    assert skipped.problems
    assert parse_tests(1, _junit(tests=1, failures=1), _coverage()).problems


def test_parse_tests_rejects_empty_mismatched_and_malformed_evidence() -> None:
    inputs = (
        ("", _coverage()), (_junit(tests=0), _coverage()),
        (_junit(tests=2), "{"), (_junit(tests=2), ""),
        (_junit(tests=2, failures=1), _coverage()),
        (_junit(tests=2).replace('tests="2"', 'tests="3"'), _coverage()),
        ("<!DOCTYPE x [<!ENTITY y SYSTEM 'file:///etc/passwd'>]><testsuite>&y;</testsuite>", _coverage()),
    )
    for junit, coverage in inputs:
        assert parse_tests(0, junit, coverage).problems


def test_parse_tests_rejects_bool_nan_out_of_range_and_zero_line_coverage() -> None:
    base = json.loads(_coverage())
    malformed_values: tuple[object, ...] = (True, float("nan"), -1, 101)
    for value in malformed_values:
        changed = json.loads(json.dumps(base))
        changed["files"]["core/a.py"]["summary"]["covered_lines"] = value
        assert parse_tests(0, _junit(), json.dumps(changed)).problems
    assert parse_tests(0, _junit(), _coverage(lines=0, covered_lines=0)).problems


def test_parse_tests_enforces_separate_line_branch_and_combined_floors() -> None:
    line_failure = parse_tests(0, _junit(), _coverage(lines=100, covered_lines=79))
    branch_failure = parse_tests(0, _junit(), _coverage(branches=100, covered_branches=79))
    assert line_failure.problems
    assert branch_failure.problems


def test_parse_tests_accepts_zero_branch_denominator_when_no_branches_exist() -> None:
    result = parse_tests(0, _junit(), _coverage(branches=0, covered_branches=0))
    assert not result.problems


def test_parse_tests_rejects_truncated_or_oversized_inputs_without_echoing_payload() -> None:
    secret = "SYNTHETIC_SECRET_DO_NOT_ECHO"
    too_large = "x" * (8 * 1024 * 1024 + 1)
    for junit, coverage in (("<testsuite>", _coverage()), (_junit(), too_large), (secret, _coverage())):
        result = parse_tests(0, junit, coverage)
        assert result.problems
        assert secret not in " ".join(result.problems)


def test_parse_tests_checks_touched_files_and_coverage_consistency() -> None:
    above_floor_aggregate = _coverage(per_file=(("core/a.py", 100, 70), ("api/b.py", 100, 100)))
    assert parse_tests(0, _junit(), above_floor_aggregate).problems
    assert parse_tests(0, _junit(), _coverage(), touched=("core/missing.py",)).problems
    inconsistent = json.loads(_coverage())
    inconsistent["totals"]["covered_lines"] = 1
    assert parse_tests(0, _junit(), json.dumps(inconsistent)).problems
    assert parse_tests(0, _junit(), _coverage(branch_coverage=False)).problems


def test_is_ready_requires_exact_order_all_stages_and_real_required_counts() -> None:
    passing = (
        StageResult("build", 0), StageResult("types", 0, count=0),
        StageResult("lint", 0, count=0),
        StageResult("tests", 0, passed=2, total=2, coverage=90.0),
        StageResult("security", 0, count=0), StageResult("diff", 0, count=0),
    )
    assert is_ready(passing)
    assert not is_ready(passing[:-1])
    assert not is_ready((passing[1], passing[0], *passing[2:]))
    assert not is_ready((passing[0], StageResult("types", 0), *passing[2:]))


def test_is_ready_rejects_invalid_test_coverage_counts_and_any_stage_problem() -> None:
    good = (
        StageResult("build", 0), StageResult("types", 0, count=0),
        StageResult("lint", 0, count=0), StageResult("tests", 0, passed=2, total=2, coverage=80),
        StageResult("security", 0, count=0), StageResult("diff", 0, count=0),
    )
    assert is_ready(good)
    for tests in (
        StageResult("tests", 0, passed=0, total=0, coverage=90),
        StageResult("tests", 0, passed=1, total=2, coverage=90),
        StageResult("tests", 0, passed=2, total=2, coverage=float("nan")),
        StageResult("tests", 0, passed=2, total=2, coverage=79.99),
    ):
        assert not is_ready((*good[:3], tests, *good[4:]))
    assert not is_ready((*good[:2], StageResult("lint", 0, count=0, problems=("bad",)), *good[3:]))


def test_format_report_has_truthful_first_line_unknowns_order_and_sanitized_issues() -> None:
    secret = "SYNTHETIC_SECRET_DO_NOT_ECHO"
    report = format_report((StageResult("types", None, problems=(secret,)),))
    lines = report.splitlines()
    assert lines[0].startswith("VERIFICATION REPORT — Build: ")
    assert "Overall: NOT READY. Issues to fix (numbered)." in lines[0]
    assert "unknown" in report
    assert secret not in report
    assert "build" in report and "security" in report and "diff" in report
    assert not is_ready((StageResult("types", None),))


def _passing_results() -> tuple[StageResult, ...]:
    return (
        StageResult("build", 0), StageResult("types", 0, count=0),
        StageResult("lint", 0, count=0),
        StageResult("tests", 0, passed=2, total=2, coverage=90.0),
        StageResult("security", 0, count=0), StageResult("diff", 0, count=0),
    )


@pytest.mark.parametrize("index", range(6))
def test_boolean_process_codes_never_satisfy_readiness(index: int) -> None:
    good = list(_passing_results())
    item = good[index]
    good[index] = StageResult(item.stage, False, item.count, item.passed, item.total, item.coverage)
    assert not is_ready(tuple(good))


def test_empty_package_modules_remain_in_coverage_denominator() -> None:
    data = json.loads(_coverage())
    data["files"]["core/__init__.py"] = {"summary": {
        "num_statements": 0, "covered_lines": 0, "num_branches": 0, "covered_branches": 0,
    }}
    result = parse_tests(0, _junit(), json.dumps(data))
    assert not result.problems


def test_report_uses_combined_application_coverage() -> None:
    result = parse_tests(0, _junit(), _coverage(lines=100, covered_lines=90, branches=100, covered_branches=80))
    assert not result.problems
    assert result.coverage == 85.0


def test_invalid_required_evidence_gets_failed_status_and_numbered_reason() -> None:
    results = list(_passing_results())
    results[-1] = StageResult("diff", 0)
    report = format_report(tuple(results))
    assert "Overall: NOT READY" in report
    assert any(line.startswith("1.") for line in report.splitlines())
    results = list(_passing_results())
    results[3] = StageResult("tests", 0, passed=1, total=2, coverage=90.0)
    assert "Tests: FAIL (1/2" in format_report(tuple(results))
    assert "Tests: FAIL (unknown/unknown, unknown%)" in format_report(())


@pytest.mark.parametrize("parser", [parse_types, parse_lint])
def test_json_parsers_reject_deep_input_without_raising(parser: Callable[[int, str], StageResult]) -> None:
    result = parser(0, "[" * 2000 + "0" + "]" * 2000)
    assert result.problems


def test_format_report_all_pass_first_line_matches_owner_format() -> None:
    results = (
        StageResult("build", 0), StageResult("types", 0, count=0),
        StageResult("lint", 0, count=0),
        StageResult("tests", 0, passed=5, total=5, coverage=88.0),
        StageResult("security", 0, count=0), StageResult("diff", 0, count=2),
    )
    assert format_report(results).splitlines()[0] == (
        "VERIFICATION REPORT — Build: PASS, Types: PASS (0), Lint: PASS (0), "
        "Tests: PASS (5/5, 88.00%), Security: PASS (0), Diff: (2 files). "
        "Overall: READY. Issues to fix (numbered)."
    )
