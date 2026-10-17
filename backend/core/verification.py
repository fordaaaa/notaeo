"""Parse bounded verification evidence without exposing its payloads."""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass

STAGES = ("build", "types", "lint", "tests", "security", "diff")
_LIMIT = 8 * 1024 * 1024


@dataclass(frozen=True)
class StageResult:
    stage: str
    returncode: int | None
    count: int | None = None
    passed: int | None = None
    total: int | None = None
    coverage: float | None = None
    problems: tuple[str, ...] = ()


def _valid_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _exit_problem(returncode: int) -> tuple[str, ...]:
    if not _valid_int(returncode):
        return ("Invalid process return code.",)
    return () if returncode == 0 else ("Command failed.",)


def _json(text: str) -> object:
    if len(text.encode("utf-8")) > _LIMIT:
        raise ValueError
    return json.loads(text, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))


def parse_types(returncode: int, output: str) -> StageResult:
    problems = list(_exit_problem(returncode))
    count: int | None = None
    try:
        data = _json(output)
        summary = data["summary"] if isinstance(data, dict) else None
        if not isinstance(summary, dict):
            raise ValueError
        errors, warnings = summary.get("errorCount"), summary.get("warningCount")
        if not _valid_int(errors) or not _valid_int(warnings):
            raise ValueError
        if not isinstance(errors, int) or not isinstance(warnings, int):
            raise ValueError
        count = errors + warnings
    except (ValueError, TypeError, KeyError, RecursionError, UnicodeError):
        problems.append("Invalid type-checker evidence.")
    return StageResult("types", returncode, count=count, problems=tuple(problems))


def parse_lint(returncode: int, output: str) -> StageResult:
    problems = list(_exit_problem(returncode))
    count: int | None = None
    try:
        data = _json(output)
        if not isinstance(data, list):
            raise ValueError
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("code"), str) or not item["code"]:
                raise ValueError
            if not isinstance(item.get("message"), str) or not item["message"]:
                raise ValueError
            loc = item.get("location")
            if not isinstance(loc, dict) or not isinstance(loc.get("row"), int) or isinstance(loc.get("row"), bool) or loc["row"] < 1:
                raise ValueError
            if not isinstance(loc.get("column"), int) or isinstance(loc.get("column"), bool) or loc["column"] < 1:
                raise ValueError
        count = len(data)
    except (ValueError, TypeError, RecursionError, UnicodeError):
        problems.append("Invalid lint evidence.")
    return StageResult("lint", returncode, count=count, problems=tuple(problems))


def _coverage_data(text: str) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    data = _json(text)
    if not isinstance(data, dict) or not isinstance(data.get("meta"), dict) or not isinstance(data.get("totals"), dict) or not isinstance(data.get("files"), dict):
        raise ValueError
    if data["meta"].get("branch_coverage") is not True:
        raise ValueError
    return data["totals"], data["files"], data["meta"]


def _counts(summary: object) -> tuple[int, int, int, int]:
    if not isinstance(summary, dict):
        raise ValueError
    fields = ("num_statements", "covered_lines", "num_branches", "covered_branches")
    raw_values = tuple(summary.get(field) for field in fields)
    if not all(_valid_int(value) for value in raw_values):
        raise ValueError
    values = tuple(value for value in raw_values if isinstance(value, int) and not isinstance(value, bool))
    if len(values) != len(fields):
        raise ValueError
    lines, covered, branches, branch_covered = values
    if covered > lines or branch_covered > branches:
        raise ValueError
    return lines, covered, branches, branch_covered


def _floor(lines: int, covered: int, branches: int, branch_covered: int) -> bool:
    return covered * 100 >= lines * 80 and (branches == 0 or branch_covered * 100 >= branches * 80)


def _junit(text: str) -> tuple[int, int, int, int]:
    if len(text.encode("utf-8")) > _LIMIT or "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError
    root = ET.fromstring(text)
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite")) if root.tag == "testsuites" else []
    if not suites:
        raise ValueError
    tests = failures = errors = skipped = cases_count = 0
    for suite in suites:
        attrs = [suite.get(k) for k in ("tests", "failures", "errors", "skipped")]
        if any(value is None or not value.isdigit() for value in attrs):
            raise ValueError
        suite_tests, suite_failures, suite_errors, suite_skipped = (int(value) for value in attrs if value is not None)
        cases = list(suite.findall("testcase"))
        if suite_tests != len(cases) or suite_failures != sum(bool(case.find("failure") is not None) for case in cases) or suite_errors != sum(bool(case.find("error") is not None) for case in cases) or suite_skipped != sum(bool(case.find("skipped") is not None) for case in cases):
            raise ValueError
        tests += suite_tests
        failures += suite_failures
        errors += suite_errors
        skipped += suite_skipped
        cases_count += len(cases)
    if tests <= 0 or cases_count != tests:
        raise ValueError
    return tests, failures, errors, skipped


def parse_tests(returncode: int, junit_xml: str, coverage_json: str, touched: tuple[str, ...] = ()) -> StageResult:
    problems = list(_exit_problem(returncode))
    passed: int | None = None
    total: int | None = None
    coverage: float | None = None
    try:
        if len(junit_xml.encode("utf-8")) > _LIMIT or len(coverage_json.encode("utf-8")) > _LIMIT:
            raise ValueError
        total, failures, errors, skipped = _junit(junit_xml)
        passed = total - failures - errors - skipped
        if passed <= 0 or failures or errors or skipped:
            problems.append("Test suite has failures, errors, or skipped tests.")
    except (ValueError, TypeError, ET.ParseError, UnicodeError):
        problems.append("Invalid test result evidence.")
    try:
        totals, files, _ = _coverage_data(coverage_json)
        parsed: dict[str, tuple[int, int, int, int]] = {}
        for filename, entry in files.items():
            if not isinstance(filename, str) or not isinstance(entry, dict):
                raise ValueError
            parsed[filename.replace("\\", "/")] = _counts(entry.get("summary"))
        app = [counts for filename, counts in parsed.items() if filename.startswith(("core/", "api/")) and filename.endswith(".py")]
        if not app:
            raise ValueError
        sums = tuple(sum(count[i] for count in parsed.values()) for i in range(4))
        total_counts = _counts(totals)
        if sums != total_counts:
            raise ValueError
        # Core and API coverage form the product denominator; supplemental paths are excluded.
        lines, covered, branches, branch_covered = (sum(row[i] for row in app) for i in range(4))
        if lines == 0:
            raise ValueError
        if not _floor(lines, covered, branches, branch_covered):
            problems.append("Application coverage is below the 80% line or branch floor.")
        denominator = lines + branches
        coverage = (covered + branch_covered) * 100.0 / denominator if denominator else covered * 100.0 / lines
        for filename in touched:
            normalized = filename.replace("\\", "/")
            row = parsed.get(normalized)
            if row is None or not normalized.endswith(".py"):
                problems.append("Touched Python file is missing from coverage evidence.")
            elif not _floor(*row):
                problems.append("A touched Python file is below the 80% line or branch floor.")
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
        problems.append("Invalid coverage evidence.")
    return StageResult("tests", returncode, passed=passed, total=total, coverage=coverage, problems=tuple(problems))


def is_ready(results: tuple[StageResult, ...]) -> bool:
    if len(results) != len(STAGES) or tuple(result.stage for result in results) != STAGES:
        return False
    for result in results:
        if not isinstance(result.returncode, int) or isinstance(result.returncode, bool) or result.returncode != 0 or result.problems:
            return False
    for result in (results[1], results[2], results[4]):
        if not _valid_int(result.count) or result.count != 0:
            return False
    tests = results[3]
    if not _valid_int(tests.passed) or not _valid_int(tests.total) or tests.passed == 0 or tests.passed != tests.total:
        return False
    if not isinstance(tests.coverage, (float, int)) or isinstance(tests.coverage, bool) or not math.isfinite(tests.coverage) or tests.coverage < 80 or tests.coverage > 100:
        return False
    return _valid_int(results[5].count)


def _stage_pass(result: StageResult) -> bool:
    return isinstance(result.returncode, int) and not isinstance(result.returncode, bool) and result.returncode == 0 and not result.problems


def _shown(value: int | float | None) -> str:
    return "unknown" if value is None else str(value)


def format_report(results: tuple[StageResult, ...]) -> str:
    by_stage = {result.stage: result for result in results if result.stage in STAGES}
    lookup = by_stage
    build = "PASS" if "build" in lookup and _stage_pass(lookup["build"]) else "FAIL"
    type_result, lint_result = lookup.get("types"), lookup.get("lint")
    types = f"{'PASS' if type_result is not None and _stage_pass(type_result) and type_result.count == 0 else 'FAIL'} ({_shown(type_result.count if type_result is not None else None)})"
    lint = f"{'PASS' if lint_result is not None and _stage_pass(lint_result) and lint_result.count == 0 else 'FAIL'} ({_shown(lint_result.count if lint_result is not None else None)})"
    tests_result = lookup.get("tests")
    tests_valid = False
    if tests_result is not None:
        tests_valid = (_stage_pass(tests_result) and
                       _valid_int(tests_result.passed) and _valid_int(tests_result.total) and
                       isinstance(tests_result.passed, int) and isinstance(tests_result.total, int) and
                       tests_result.passed > 0 and tests_result.passed == tests_result.total and
                       isinstance(tests_result.coverage, (int, float)) and not isinstance(tests_result.coverage, bool) and
                       math.isfinite(tests_result.coverage) and 80 <= tests_result.coverage <= 100)
    tests = ("FAIL (unknown/unknown, unknown%)" if tests_result is None else
             f"{'PASS' if tests_valid else 'FAIL'} ({_shown(tests_result.passed)}/{_shown(tests_result.total)}, {_shown(tests_result.coverage) if tests_result.coverage is None else f'{tests_result.coverage:.2f}'}%)")
    security_result = lookup.get("security")
    security = f"{'PASS' if security_result is not None and _stage_pass(security_result) and security_result.count == 0 else 'FAIL'} ({_shown(security_result.count if security_result is not None else None)})"
    diff_result = lookup.get("diff")
    diff = _shown(diff_result.count if diff_result is not None else None)
    ready = is_ready(results)
    first = (f"VERIFICATION REPORT — Build: {build}, Types: {types}, Lint: {lint}, Tests: {tests}, "
             f"Security: {security}, Diff: ({diff} files). Overall: {'READY' if ready else 'NOT READY'}. Issues to fix (numbered).")
    issues: list[str] = []
    if len(results) != len(STAGES) or tuple(item.stage for item in results) != STAGES:
        issues.append("Stage evidence is missing, duplicated, or out of order.")
    for stage in STAGES:
        result = lookup.get(stage)
        if result is None:
            issues.append(f"{stage} evidence is missing.")
        elif not _stage_pass(result) and result.problems:
            issues.extend(f"{stage}: evidence problem" for _ in result.problems)
        elif not _stage_pass(result):
            issues.append(f"{stage} did not pass.")
        elif stage in ("types", "lint", "security") and (not _valid_int(result.count) or result.count != 0):
            issues.append(f"{stage}: required count is invalid or nonzero.")
        elif stage == "diff" and not _valid_int(result.count):
            issues.append("diff: file count is unknown or invalid.")
        elif stage == "tests" and not tests_valid:
            issues.append("tests: required passing counts or coverage are invalid.")
    lines = [first]
    if not ready:
        lines.extend(f"{index}. {problem}" for index, problem in enumerate(issues, 1))
    return "\n".join(lines)
