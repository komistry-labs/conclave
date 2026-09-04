"""Machine-report honesty tests for the Increment 20D evidence generator."""

from __future__ import annotations

from pathlib import Path
import io
import json
import sys
import tarfile
import zipfile

import pytest
import tools.conformance_evidence as evidence_tool

from tools.conformance_evidence import (
    MAX_JUNIT_BYTES,
    digest,
    junit_report,
    main,
    scan_package,
)


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
        _junit(
            tmp_path,
            f'<testcase classname="tests.test_bad" name="test_bad"><{element}/></testcase>',
        ),
        "ubuntu-latest-py3.13",
    )
    assert report["status"] == "FAIL"
    assert report["reason_codes"] == ["TEST_FAILURES_OR_ERRORS"]


def test_unexpected_skip_is_not_run_and_blocks_tool_pass(tmp_path: Path):
    report = junit_report(
        _junit(
            tmp_path,
            '<testcase classname="tests.test_required" name="test_required"><skipped/></testcase>',
        ),
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


def test_oversized_junit_is_rejected_before_parsing(tmp_path: Path):
    path = tmp_path / "pytest-report.xml"
    path.write_bytes(b" " * (MAX_JUNIT_BYTES + 1))

    with pytest.raises(ValueError, match="exceeds the 16 MiB limit"):
        junit_report(path, "ubuntu-latest-py3.13")


def test_unknown_platform_cannot_choose_an_unbounded_skip_policy(tmp_path: Path):
    path = _junit(tmp_path, '<testcase classname="tests.test_ok" name="test_ok"/>')
    with pytest.raises(ValueError, match="unsupported"):
        junit_report(path, "linux-local")


def test_ubuntu_minimum_platform_accepts_no_skips_and_rejects_every_skip(
    tmp_path: Path,
):
    platform = "ubuntu-latest-py3.12"
    assert (
        junit_report(
            _junit(tmp_path, '<testcase classname="tests.test_ok" name="test_ok"/>'),
            platform,
        )["status"]
        == "PASS"
    )
    report = junit_report(
        _junit(
            tmp_path,
            '<testcase classname="tests.test_ok" name="test_ok"><skipped/></testcase>',
        ),
        platform,
    )
    assert report["status"] == "NOT_RUN" and report["unexpected_skips"] == [
        "tests.test_ok::test_ok"
    ]


def _package(path: Path, name: str, data: bytes) -> None:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(name, data)
    else:
        with tarfile.open(path, "w:gz") as archive:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


@pytest.mark.parametrize("suffix", ["pkg.whl", "pkg.tar.gz"])
@pytest.mark.parametrize(
    ("name", "data", "code"),
    [
        ("pkg/key.txt", b"-----BEGIN " + b"PRIVATE KEY-----", "PRIVATE_KEY_MATERIAL"),
        (
            "pkg/ssh.txt",
            b"-----BEGIN OPENSSH " + b"PRIVATE KEY-----",
            "PRIVATE_KEY_MATERIAL",
        ),
        ("pkg/archive.p12", b"synthetic container", "PKCS12_CONTAINER"),
        (
            "pkg/neutral.bin",
            b"\x30\x16\x02\x01\x03\x30\x11"
            b"\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x01\xa0\x04\x04\x02\x00\x00",
            "PKCS12_CONTAINER",
        ),
        ("pkg/config.txt", b"id=" + b"AKIA" + b"A" * 16, "AWS_ACCESS_KEY"),
    ],
)
def test_member_secret_scanning_reads_both_package_formats(
    tmp_path: Path, suffix: str, name: str, data: bytes, code: str
):
    package = tmp_path / suffix
    _package(package, name, data)
    assert any(code in finding for finding in scan_package(package)["findings"])


@pytest.mark.parametrize("suffix", ["pkg.whl", "pkg.tar.gz"])
def test_clean_package_members_pass(tmp_path: Path, suffix: str):
    package = tmp_path / suffix
    _package(package, "pkg/module.py", b"value = 1\n")
    assert scan_package(package)["findings"] == []


@pytest.mark.parametrize("suffix", ["pkg.whl", "pkg.tar.gz"])
def test_package_member_count_limit_fails_closed(tmp_path: Path, monkeypatch, suffix: str):
    package = tmp_path / suffix
    _package(package, "pkg/member", b"1")
    monkeypatch.setattr(evidence_tool, "MAX_ARCHIVE_MEMBERS", 0)
    with pytest.raises(ValueError, match="member-count"):
        scan_package(package)


@pytest.mark.parametrize("suffix", ["pkg.whl", "pkg.tar.gz"])
def test_package_member_size_limit_fails_closed(tmp_path: Path, monkeypatch, suffix: str):
    package = tmp_path / suffix
    _package(package, "pkg/member", b"1234")
    monkeypatch.setattr(evidence_tool, "MAX_MEMBER_BYTES", 3)
    with pytest.raises(ValueError, match="decompressed-size"):
        scan_package(package)


@pytest.mark.parametrize("suffix", ["pkg.whl", "pkg.tar.gz"])
def test_package_aggregate_limit_fails_closed(tmp_path: Path, monkeypatch, suffix: str):
    package = tmp_path / suffix
    _package(package, "pkg/member", b"1234")
    monkeypatch.setattr(evidence_tool, "MAX_ARCHIVE_BYTES", 3)
    with pytest.raises(ValueError, match="aggregate"):
        scan_package(package)


def test_final_index_binds_probe_exactly_and_never_self_references(
    tmp_path: Path, monkeypatch
):
    dist, output = tmp_path / "dist", tmp_path / "evidence"
    dist.mkdir()
    output.mkdir()
    wheel, sdist = (
        dist / "conclave-0.8.0-py3-none-any.whl",
        dist / "conclave-0.8.0.tar.gz",
    )
    _package(wheel, "conclave/module.py", b"value = 1\n")
    _package(sdist, "conclave-0.8.0/src/conclave/module.py", b"value = 1\n")
    junit = _junit(tmp_path, '<testcase classname="tests.test_ok" name="test_ok"/>')
    probe = output / "installed-wheel-probe.json"
    probe.write_text(
        json.dumps(
            {
                "schema": "conclave-installed-wheel-probe/0.8.0",
                "status": "PASS",
                "wheel_sha256": digest(wheel),
                "commands": [
                    {
                        "name": "help",
                        "command": ["conclave", "--help"],
                        "returncode": 0,
                        "stdout": "Usage",
                        "stderr": "",
                    },
                    {
                        "name": "version",
                        "command": ["conclave", "version"],
                        "returncode": 0,
                        "stdout": "conclave 0.8.0\nschema  task-packet/0.1.0",
                        "stderr": "",
                    },
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    argv = [
        "conformance_evidence.py",
        "--root",
        str(Path(__file__).parents[1]),
        "--dist",
        str(dist),
        "--junit",
        str(junit),
        "--probe",
        str(probe),
        "--output",
        str(output),
        "--platform-id",
        "ubuntu-latest-py3.12",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    assert main() == 0
    first = (output / "evidence-index.json").read_bytes()
    index = json.loads(first)
    refs = [item["reference"] for item in index["reports"]]
    assert "installed-wheel-probe.json" in refs and "evidence-index.json" not in refs
    monkeypatch.setattr(sys, "argv", argv)
    assert main() == 0
    assert (output / "evidence-index.json").read_bytes() == first
