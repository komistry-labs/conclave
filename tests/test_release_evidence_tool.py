"""Security and determinism tests for v0.8.0 release evidence tooling."""

from __future__ import annotations

import io
import json
import stat
import tarfile
import zipfile
from pathlib import Path
import pytest
import tools.release_evidence as release_tool

from tools.conformance_evidence import SCANNER_VERSION
from tools.release_evidence import (
    MANIFEST_NAME,
    PLATFORMS,
    content_manifest,
    create_bundle,
    encode,
    final_manifest,
    hash_file,
    safe_name,
    scan_bundle,
    write_json,
)


def _archive(path: Path, name: str, data: bytes):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(name, data)
    else:
        with tarfile.open(path, "w:gz") as archive:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def _fixture(tmp_path: Path):
    wheel, sdist = (
        tmp_path / "conclave-0.8.0-py3-none-any.whl",
        tmp_path / "conclave-0.8.0.tar.gz",
    )
    _archive(wheel, "conclave/__init__.py", b"version='0.8.0'\n")
    _archive(sdist, "conclave-0.8.0/src/conclave/__init__.py", b"version='0.8.0'\n")
    scan = tmp_path / "member-scan.json"
    write_json(
        scan,
        {
            "schema": SCANNER_VERSION,
            "status": "PASS",
            "findings": [],
            "packages": [
                {"name": wheel.name, "content_hash": hash_file(wheel)},
                {"name": sdist.name, "content_hash": hash_file(sdist)},
            ],
        },
    )
    sources = {wheel.name: wheel, sdist.name: sdist, scan.name: scan}
    platforms = []
    for number, platform in enumerate(sorted(PLATFORMS), 1):
        evidence = tmp_path / f"{platform}-index.json"
        write_json(evidence, {"status": "PASS", "platform_id": platform})
        sources[evidence.name] = evidence
        platforms.append(
            {
                "platform_id": platform,
                "workflow_run_id": f"run-{number}",
                "job_id": f"job-{number}",
                "artifact_id": f"artifact-{number}",
                "evidence_index": {
                    "reference": evidence.name,
                    "sha256": hash_file(evidence),
                },
            }
        )
    for name in (
        "protection-before.json",
        "protection-after.json",
        "requirements-v0.8.0.lock",
    ):
        path = tmp_path / name
        path.write_text("clean public evidence\n", encoding="utf-8")
        sources[name] = path
    spec = {
        "release_commit": "a" * 40,
        "protocol": {
            "reference": "RELEASE-PROTOCOL-v0.8.0.md",
            "sha256": "sha256:" + "b" * 64,
        },
        "release_notes": {
            "reference": "RELEASE-NOTES-v0.8.0.md",
            "sha256": "sha256:" + "c" * 64,
        },
        "platforms": platforms,
        "canonical_packages": {
            "wheel": {
                "reference": wheel.name,
                "sha256": hash_file(wheel),
                "member_scan_report": {
                    "reference": scan.name,
                    "sha256": hash_file(scan),
                },
            },
            "sdist": {
                "reference": sdist.name,
                "sha256": hash_file(sdist),
                "member_scan_report": {
                    "reference": scan.name,
                    "sha256": hash_file(scan),
                },
            },
        },
        "protection": {
            "snapshot": {
                "reference": "protection-before.json",
                "sha256": hash_file(sources["protection-before.json"]),
            },
            "restoration": {
                "reference": "protection-after.json",
                "sha256": hash_file(sources["protection-after.json"]),
            },
        },
        "qualification_reports": [{"reference": scan.name, "sha256": hash_file(scan)}],
        "dependency_lock": {
            "reference": "requirements-v0.8.0.lock",
            "sha256": hash_file(sources["requirements-v0.8.0.lock"]),
        },
        "bundle_members": [
            {"reference": name, "sha256": hash_file(path)}
            for name, path in sorted(sources.items())
        ],
    }
    manifest = tmp_path / MANIFEST_NAME
    write_json(manifest, content_manifest(spec))
    return manifest, sources


def test_content_manifest_is_canonical_and_requires_all_platforms(tmp_path: Path):
    manifest, _ = _fixture(tmp_path)
    value = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest.read_bytes() == encode(value)
    value["platforms"].pop()
    with pytest.raises(ValueError, match="four exact platform"):
        content_manifest(value)


def test_bundle_and_scan_are_deterministic_and_bind_nested_packages(tmp_path: Path):
    manifest, sources = _fixture(tmp_path)
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    report = create_bundle(manifest, sources, first)
    report2 = create_bundle(manifest, sources, second)
    assert first.read_bytes() == second.read_bytes()
    assert report == report2 and report["status"] == "PASS"
    assert report["zip_sha256"] == hash_file(first)
    assert set(report["canonical_package_hashes"]) == {"wheel", "sdist"}
    assert [m["reference"] for m in report["members"]] == sorted(
        m["reference"] for m in report["members"]
    )


def test_final_manifest_is_external_exact_and_self_reference_free(tmp_path: Path):
    content, sources = _fixture(tmp_path)
    bundle, scan, final = (
        tmp_path / "bundle.zip",
        tmp_path / "bundle-scan.json",
        tmp_path / "final.json",
    )
    write_json(scan, create_bundle(content, sources, bundle))
    value = final_manifest(content, bundle, scan, final)
    assert value["qualification_zip"]["sha256"] == hash_file(bundle)
    assert value["bundle_scan_report"]["sha256"] == hash_file(scan)
    assert final.name not in final.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="itself"):
        final_manifest(content, bundle, scan, scan)


def test_final_manifest_rejects_a_forged_pass_scan(tmp_path: Path):
    content, sources = _fixture(tmp_path)
    bundle, scan = tmp_path / "bundle.zip", tmp_path / "bundle-scan.json"
    forged = create_bundle(content, sources, bundle)
    forged["scanner_version"] = "forged-scanner/9.9.9"
    write_json(scan, forged)
    with pytest.raises(ValueError, match="exact deterministic PASS"):
        final_manifest(content, bundle, scan, tmp_path / "final.json")


def test_final_manifest_requires_the_exact_content_embedded_in_bundle(tmp_path: Path):
    content, sources = _fixture(tmp_path)
    bundle, scan = tmp_path / "bundle.zip", tmp_path / "bundle-scan.json"
    write_json(scan, create_bundle(content, sources, bundle))
    changed = json.loads(content.read_text(encoding="utf-8"))
    changed["release_commit"] = "f" * 40
    write_json(content, changed)
    with pytest.raises(ValueError, match="embedded content"):
        final_manifest(content, bundle, scan, tmp_path / "final.json")


@pytest.mark.parametrize(
    "name", ["../escape", "/absolute", "C:/drive", "folder\\member", "folder/../member"]
)
def test_unsafe_bundle_paths_are_rejected(name: str):
    with pytest.raises(ValueError, match="unsafe"):
        safe_name(name)


def test_duplicate_and_symlink_members_are_rejected(tmp_path: Path):
    duplicate = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(duplicate, "w") as archive:
        archive.writestr("same", b"one")
        archive.writestr("SAME", b"two")
    with pytest.raises(ValueError, match="duplicate"):
        scan_bundle(duplicate)
    linked = tmp_path / "linked.zip"
    with zipfile.ZipFile(linked, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"target")
    with pytest.raises(ValueError, match="non-regular"):
        scan_bundle(linked)


def test_bundle_member_count_limit_fails_closed(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "count.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("one", b"1")
    monkeypatch.setattr(release_tool, "MAX_BUNDLE_MEMBERS", 0)
    with pytest.raises(ValueError, match="member-count"):
        scan_bundle(bundle)


def test_bundle_member_size_limit_fails_closed(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "member-size.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("member", b"1234")
    monkeypatch.setattr(release_tool, "MAX_BUNDLE_MEMBER_BYTES", 3)
    with pytest.raises(ValueError, match="oversized"):
        scan_bundle(bundle)


def test_bundle_aggregate_limit_fails_closed(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "aggregate.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("member", b"1234")
    monkeypatch.setattr(release_tool, "MAX_BUNDLE_BYTES", 3)
    with pytest.raises(ValueError, match="aggregate"):
        scan_bundle(bundle)


def test_bundle_secret_finding_cannot_pass(tmp_path: Path):
    manifest, sources = _fixture(tmp_path)
    secret = tmp_path / "ordinary.txt"
    secret.write_bytes(b"-----BEGIN " + b"PRIVATE KEY-----")
    sources[secret.name] = secret
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["bundle_members"].append(
        {"reference": secret.name, "sha256": hash_file(secret)}
    )
    write_json(manifest, value)
    report = create_bundle(manifest, sources, tmp_path / "secret.zip")
    assert report["status"] == "FAIL"
    assert any("PRIVATE_KEY_MATERIAL" in finding for finding in report["findings"])
