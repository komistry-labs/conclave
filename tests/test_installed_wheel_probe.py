"""Deterministic tests for installed-wheel CLI probe evaluation."""

from tools.installed_wheel_probe import (
    EXPECTED_VERSION,
    REQUIRED_PUBLICATION_MEMBERS,
    build_report,
    command_record,
    inspect_wheel_inventory,
    normalize,
    prepare_probe_environment,
    prepare_publication_probe,
    validate_wheelhouse,
)
import io
import subprocess
import zipfile
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
        {
            "name": "github_publication_probe",
            "command": [
                "python",
                "-I",
                "external-publication-fixture.py",
            ],
            "returncode": 0,
            "stdout": "github-publication-probe-ok",
            "stderr": "",
        },
    ]


def _inventory():
    return {
        "member_count": 12,
        "required_publication_members": {
            suffix: {"member": suffix, "sha256": "sha256:" + "a" * 64}
            for suffix in REQUIRED_PUBLICATION_MEMBERS
        },
        "prohibited_members": [],
    }


def test_probe_passes_only_exact_help_and_version_contract():
    report = build_report("sha256:" + "a" * 64, _commands(), _inventory())
    assert report["status"] == "PASS"
    assert report["commands"][1]["stdout"].splitlines() == [
        "conclave 0.8.0",
        "schema  task-packet/0.1.0",
    ]


def test_wrong_version_fails():
    assert (
        build_report(
            "sha256:" + "a" * 64,
            _commands("conclave 0.7.0\nschema  task-packet/0.1.0"),
            _inventory(),
        )["status"]
        == "FAIL"
    )


def test_command_error_or_stderr_fails():
    assert (
        build_report(
            "sha256:" + "a" * 64,
            _commands(version_code=2, version_err="failure"),
            _inventory(),
        )["status"]
        == "FAIL"
    )


def _wheel_bytes(members: tuple[str, ...]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for member in members:
            archive.writestr(member, b"fixture-free-runtime")
    return output.getvalue()


def test_wheel_inventory_requires_publication_runtime_and_excludes_test_support():
    inventory = inspect_wheel_inventory(_wheel_bytes(REQUIRED_PUBLICATION_MEMBERS))
    assert set(inventory["required_publication_members"]) == set(
        REQUIRED_PUBLICATION_MEMBERS
    )
    assert inventory["prohibited_members"] == []

    with pytest.raises(ValueError, match="test support"):
        inspect_wheel_inventory(
            _wheel_bytes(
                REQUIRED_PUBLICATION_MEMBERS + ("conclave/fixtures/replies.json",)
            )
        )

    with pytest.raises(ValueError, match="fixture constructor"):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            for member in REQUIRED_PUBLICATION_MEMBERS:
                content = (
                    b"class Loopback: pass"
                    if member.endswith("github_publication_engine.py")
                    else b"fixture-free-runtime"
                )
                archive.writestr(member, content)
        inspect_wheel_inventory(output.getvalue())


def test_report_fails_without_exact_package_inventory():
    missing = _inventory()
    missing["required_publication_members"] = {}
    assert build_report("sha256:" + "a" * 64, _commands(), missing)["status"] == "FAIL"

    forged = _inventory()
    forged["required_publication_members"][REQUIRED_PUBLICATION_MEMBERS[0]][
        "sha256"
    ] = "not-a-digest"
    assert build_report("sha256:" + "a" * 64, _commands(), forged)["status"] == "FAIL"


def test_full_publication_probe_is_staged_outside_the_installed_package(tmp_path):
    probe = prepare_publication_probe(tmp_path)
    source = probe.read_text(encoding="utf-8")
    assert probe.parent == tmp_path
    assert "evaluate_governed_publication" in source
    assert "github_proposal_publication_fixture_verified" in source
    assert "MUTATION_OUTCOME_AMBIGUOUS" in source
    assert 'evidence.glob("admission-*.json")' in source
    assert 'evidence.glob("result-*.json")' in source
    assert "source_credential_lease_evidence_record" in source
    assert "PublicationResponse" not in source
    assert "root = Path(folder).resolve(strict=True)" in source


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


def test_probe_stages_wheel_after_environment_clear(tmp_path, monkeypatch):
    root = tmp_path / "probe"

    def simulate_clear(_builder, target):
        target.mkdir(parents=True, exist_ok=True)
        assert list(target.iterdir()) == []

    monkeypatch.setattr("venv.EnvBuilder.create", simulate_clear)
    canonical_root, captured, python, executable = prepare_probe_environment(
        root, "conclave.whl", b"immutable-wheel"
    )

    assert canonical_root == root.resolve(strict=True)
    assert captured.parent.parent == canonical_root
    assert python.is_relative_to(canonical_root)
    assert executable.is_relative_to(canonical_root)
    assert captured.read_bytes() == b"immutable-wheel"
