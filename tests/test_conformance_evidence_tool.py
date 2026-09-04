"""Machine-report honesty tests for the Increment 20D evidence generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.conformance_evidence import junit_report


def _junit(tmp_path: Path, cases: str) -> Path:
    path = tmp_path / "pytest-report.xml"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuites><testsuite name="pytest">{cases}</testsuite></testsuites>',
        encoding="utf-8",
    )
    return path


def test_passing_junit_is_derived_as_pass(tmp_path: Path):
    report = junit_report(
        _junit(tmp_path, '<testcase classname="tests.test_ok" name="test_ok"/>'),
        "ubuntu-latest-py3.13",
    )
    assert report["status"] == "PASS"
    assert report["tests"] == 1 and report["failures"] == 0
    assert report["reason_codes"] == []


@pytest.mark.parametrize("element", ["failure", "error"])
def test_failure_or_error_junit_is_derived_as_fail(tmp_path: Path, element: str):
    report = junit_report(
        _junit(tmp_path, f'<testcase classname="tests.test_bad" name="test_bad"><{element}/></testcase>'),
        "ubuntu-latest-py3.13",
    )
    assert report["status"] == "FAIL"
    assert report["reason_codes"] == ["TEST_FAILURES_OR_ERRORS"]


def test_unexpected_skip_is_not_run_and_blocks_tool_pass(tmp_path: Path):
    report = junit_report(
        _junit(tmp_path, '<testcase classname="tests.test_required" name="test_required"><skipped/></testcase>'),
        "macos-latest-py3.12",
    )
    assert report["status"] == "NOT_RUN"
    assert report["reason_codes"] == ["UNEXPECTED_TEST_SKIP"]
    assert report["unexpected_skips"] == ["tests.test_required::test_required"]


def test_only_two_documented_windows_capability_skips_are_allowed(tmp_path: Path):
    cases = (
        '<testcase classname="tests.test_configuration" '
        'name="test_symlink_profile_reference_is_rejected_when_supported"><skipped/></testcase>'
        '<testcase classname="tests.test_evidence" '
        'name="test_artifact_symlink_or_reparse_escape_is_refused"><skipped/></testcase>'
    )
    report = junit_report(_junit(tmp_path, cases), "windows-latest-py3.12")
    assert report["status"] == "PASS"
    assert report["skipped"] == 2
    assert len(report["allowed_skips_observed"]) == 2
    assert report["unexpected_skips"] == []


@pytest.mark.parametrize("content", ["", "not xml", "<testsuites/>"])
def test_empty_malformed_or_caseless_junit_is_rejected(tmp_path: Path, content: str):
    path = tmp_path / "pytest-report.xml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        junit_report(path, "ubuntu-latest-py3.13")


def test_unknown_platform_cannot_choose_an_unbounded_skip_policy(tmp_path: Path):
    path = _junit(tmp_path, '<testcase classname="tests.test_ok" name="test_ok"/>')
    with pytest.raises(ValueError, match="unsupported"):
        junit_report(path, "linux-local")
