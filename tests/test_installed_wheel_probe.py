"""Deterministic tests for installed-wheel CLI probe evaluation."""

from tools.installed_wheel_probe import (
    EXPECTED_VERSION,
    build_report,
    command_record,
    normalize,
    validate_wheelhouse,
)
import subprocess
import pytest


def _commands(version=EXPECTED_VERSION, version_code=0, version_err=""):
    return [
        {
            "name": "help",
            "command": ["conclave", "--help"],
            "returncode": 0,
            "stdout": "Usage: conclave",
            "stderr": "",
        },
        {
            "name": "version",
            "command": ["conclave", "version"],
            "returncode": version_code,
            "stdout": version,
            "stderr": version_err,
        },
    ]


def test_probe_passes_only_exact_help_and_version_contract():
    report = build_report("sha256:" + "a" * 64, _commands())
    assert report["status"] == "PASS"
    assert report["commands"][1]["stdout"].splitlines() == [
        "conclave 0.8.0",
        "schema  task-packet/0.1.0",
    ]


def test_wrong_version_fails():
    assert (
        build_report(
            "sha256:" + "a" * 64, _commands("conclave 0.7.0\nschema  task-packet/0.1.0")
        )["status"]
        == "FAIL"
    )


def test_command_error_or_stderr_fails():
    assert (
        build_report(
            "sha256:" + "a" * 64, _commands(version_code=2, version_err="failure")
        )["status"]
        == "FAIL"
    )


def test_normalization_and_recording_are_platform_independent():
    completed = subprocess.CompletedProcess([], 0, "one  \r\ntwo\r\n", "")
    record = command_record("version", ["conclave", "version"], completed)
    assert record == {
        "name": "version",
        "command": ["conclave", "version"],
        "returncode": 0,
        "stdout": "one\ntwo",
        "stderr": "",
    }
    assert normalize("\r\n") == ""


def test_wheelhouse_must_be_bounded_regular_packages(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "dependency.whl").write_bytes(b"fixture")
    assert validate_wheelhouse(wheelhouse) == wheelhouse.resolve()
    (wheelhouse / "notes.txt").write_text("not a package", encoding="utf-8")
    with pytest.raises(ValueError, match="non-package"):
        validate_wheelhouse(wheelhouse)


def test_empty_wheelhouse_is_rejected(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    with pytest.raises(ValueError, match="empty"):
        validate_wheelhouse(wheelhouse)
