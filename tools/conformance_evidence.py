"""Create bounded, secret-free conformance evidence from local build outputs."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import re
import stat
import tarfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

FORBIDDEN_PACKAGE_MARKERS = (
    "tests/",
    "test_",
    "fixture_broker",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".pkcs12",
    ".idmk",
    ".env",
    "token",
    "certificate",
)
RUNTIME_FILES = (
    "src/conclave/configuration.py",
    "src/conclave/sandbox_transport.py",
    "src/conclave/sandbox_recovery.py",
    "src/conclave/conformance.py",
)
TRANSPORT_FILES = RUNTIME_FILES[1:]
MAX_JUNIT_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 256
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
SCANNER_VERSION = "conclave-secret-member-scan/0.8.0"
PLATFORM_IDS = {
    "windows-latest-py3.12",
    "ubuntu-latest-py3.12",
    "ubuntu-latest-py3.13",
    "macos-latest-py3.12",
}
ALLOWED_SKIPS = {
    "windows-latest-py3.12": {
        "tests.test_configuration::test_symlink_profile_reference_is_rejected_when_supported",
        "tests.test_evidence::test_artifact_symlink_or_reparse_escape_is_refused",
    },
    "ubuntu-latest-py3.12": set(),
    "ubuntu-latest-py3.13": set(),
    "macos-latest-py3.12": set(),
}
PRIVATE_MARKERS = tuple(
    f"-----BEGIN {kind}PRIVATE KEY-----".encode()
    for kind in ("", "RSA ", "EC ", "DSA ", "OPENSSH ")
)
CREDENTIAL_PATTERNS = (
    (
        "AWS_ACCESS_KEY",
        re.compile(rb"(?<![A-Z0-9])(AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    ),
    (
        "GITHUB_TOKEN",
        re.compile(
            rb"(?<![A-Za-z0-9_])(gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{40,255})"
        ),
    ),
    (
        "OPENAI_API_KEY",
        re.compile(
            rb"(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])"
        ),
    ),
)


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def emit(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def secret_findings(name: str, data: bytes) -> list[str]:
    found = [
        f"PRIVATE_KEY_MATERIAL:{name}" for marker in PRIVATE_MARKERS if marker in data
    ]
    pkcs12_content_info_oid = b"\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x01"
    pkcs12_der = (
        data.startswith(b"\x30")
        and b"\x02\x01\x03" in data[:16]
        and pkcs12_content_info_oid in data
    )
    if name.lower().endswith((".p12", ".pfx", ".pkcs12")) or pkcs12_der:
        found.append(f"PKCS12_CONTAINER:{name}")
    found.extend(
        f"{label}:{name}"
        for label, pattern in CREDENTIAL_PATTERNS
        if pattern.search(data)
    )
    return sorted(set(found))


def _bounded_member(name: str, stream, declared: int) -> bytes:
    if declared < 0 or declared > MAX_MEMBER_BYTES:
        raise ValueError(f"archive member exceeds decompressed-size limit: {name}")
    data = stream.read(MAX_MEMBER_BYTES + 1)
    if len(data) > MAX_MEMBER_BYTES or len(data) != declared:
        raise ValueError(f"archive member size is invalid: {name}")
    return data


def scan_package(path: Path) -> dict:
    raw, names, findings, total, count = path.read_bytes(), [], [], 0, 0
    if path.suffix == ".whl":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                raise ValueError("archive member-count limit exceeded")
            seen = set()
            for info in infos:
                count += 1
                if info.filename in seen:
                    raise ValueError(
                        f"duplicate archive member is forbidden: {info.filename}"
                    )
                seen.add(info.filename)
                if info.flag_bits & 1:
                    raise ValueError(
                        f"encrypted archive member is forbidden: {info.filename}"
                    )
                if info.is_dir():
                    continue
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and stat.S_IFMT(mode) and not stat.S_ISREG(mode):
                    raise ValueError(
                        f"non-regular archive member is forbidden: {info.filename}"
                    )
                data = _bounded_member(
                    info.filename, archive.open(info), info.file_size
                )
                total += len(data)
                names.append(info.filename)
                findings += secret_findings(info.filename, data)
                if total > MAX_ARCHIVE_BYTES:
                    raise ValueError(
                        "archive aggregate decompressed-size limit exceeded"
                    )
    else:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            infos = archive.getmembers()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                raise ValueError("archive member-count limit exceeded")
            for info in infos:
                count += 1
                if info.isdir():
                    continue
                if not info.isfile():
                    raise ValueError(
                        f"non-regular archive member is forbidden: {info.name}"
                    )
                stream = archive.extractfile(info)
                if stream is None:
                    raise ValueError(f"archive member cannot be read: {info.name}")
                data = _bounded_member(info.name, stream, info.size)
                total += len(data)
                names.append(info.name)
                findings += secret_findings(info.name, data)
                if total > MAX_ARCHIVE_BYTES:
                    raise ValueError(
                        "archive aggregate decompressed-size limit exceeded"
                    )
    return {
        "artifact": path.name,
        "content_hash": digest_bytes(raw),
        "members": sorted(names),
        "member_count": count,
        "decompressed_bytes": total,
        "findings": sorted(set(findings)),
    }


def inventory(path: Path) -> list[str]:
    return scan_package(path)["members"]


def static_scan(root: Path) -> dict:
    findings, forbidden_imports, forbidden_calls = (
        [],
        {"cryptography", "jose", "nacl"},
        {"eval", "exec", "compile", "__import__"},
    )
    for relative in RUNTIME_FILES:
        tree = ast.parse(
            (root / relative).read_text(encoding="utf-8"), filename=relative
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                findings += [
                    f"FORBIDDEN_IMPORT:{relative}:{item.name}"
                    for item in node.names
                    if item.name.split(".")[0] in forbidden_imports
                ]
            elif (
                isinstance(node, ast.ImportFrom)
                and (node.module or "").split(".")[0] in forbidden_imports
            ):
                findings.append(f"FORBIDDEN_IMPORT:{relative}:{node.module}")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in forbidden_calls
            ):
                findings.append(f"DYNAMIC_EXECUTION:{relative}:{node.func.id}")
    for relative in TRANSPORT_FILES:
        text = (root / relative).read_text(encoding="utf-8")
        if "import subprocess" in text or "import os.system" in text:
            findings.append(f"TRANSPORT_SHELL_SURFACE:{relative}")
    return {
        "schema": "conclave-20d-static-scan/0.1.0",
        "status": "PASS" if not findings else "FAIL",
        "findings": sorted(findings),
    }


def junit_report(path: Path, platform_id: str) -> dict:
    if platform_id not in PLATFORM_IDS:
        raise ValueError("unsupported 20D platform identifier")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_JUNIT_BYTES:
        raise ValueError("JUnit report is empty or exceeds the 16 MiB limit")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("JUnit report is malformed") from exc
    cases = list(root.iter("testcase"))
    if not cases:
        raise ValueError("JUnit report contains no test cases")
    failures = sum(len(c.findall("failure")) for c in cases)
    errors = sum(len(c.findall("error")) for c in cases)
    skipped = [
        f"{c.attrib.get('classname', '')}::{c.attrib.get('name', '')}"
        for c in cases
        if c.find("skipped") is not None
    ]
    allowed, unexpected = (
        ALLOWED_SKIPS[platform_id],
        sorted(set(skipped) - ALLOWED_SKIPS[platform_id]),
    )
    reasons = (["TEST_FAILURES_OR_ERRORS"] if failures or errors else []) + (
        ["UNEXPECTED_TEST_SKIP"] if unexpected else []
    )
    return {
        "schema": "conclave-20d-test-report/0.1.0",
        "status": "FAIL" if failures or errors else "NOT_RUN" if unexpected else "PASS",
        "platform_id": platform_id,
        "tests": len(cases),
        "failures": failures,
        "errors": errors,
        "skipped": len(skipped),
        "allowed_skips_observed": sorted(set(skipped) & allowed),
        "unexpected_skips": unexpected,
        "reason_codes": reasons,
        "junit_reference": path.name,
        "junit_hash": digest(path),
    }


def validate_probe(path: Path, wheel_hash: str) -> dict:
    raw = path.read_bytes()
    if not raw or len(raw) > 1024 * 1024:
        raise ValueError("installed-wheel probe is empty or oversized")
    value = json.loads(raw)
    if value.get("schema") != "conclave-installed-wheel-probe/0.8.0":
        raise ValueError("installed-wheel probe schema is invalid")
    if value.get("status") != "PASS" or value.get("wheel_sha256") != wheel_hash:
        raise ValueError("installed-wheel probe did not pass for the exact wheel")
    commands = value.get("commands")
    if not isinstance(commands, list) or [c.get("name") for c in commands] != [
        "help",
        "version",
    ]:
        raise ValueError("installed-wheel probe commands are incomplete")
    if any(c.get("returncode") != 0 or c.get("stderr") != "" for c in commands):
        raise ValueError("installed-wheel probe contains a failed command")
    if not commands[0].get("stdout"):
        raise ValueError("installed-wheel help output is empty")
    if commands[1].get("stdout") != "conclave 0.8.0\nschema  task-packet/0.1.0":
        raise ValueError("installed-wheel version output is invalid")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform-id", required=True)
    args = parser.parse_args()
    root, dist, output = args.root.resolve(), args.dist.resolve(), args.output.resolve()
    if args.platform_id not in PLATFORM_IDS:
        raise SystemExit("unsupported 20D platform identifier")
    output.mkdir(parents=True, exist_ok=True)
    artifacts = sorted([*dist.glob("*.whl"), *dist.glob("*.tar.gz")])
    wheels = [p for p in artifacts if p.suffix == ".whl"]
    sdists = [p for p in artifacts if p.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one wheel and one sdist")
    packages, package_findings, scan_findings = [], [], []
    for artifact in artifacts:
        scan = scan_package(artifact)
        inventory_path = output / f"{artifact.name}.inventory.json"
        emit(
            inventory_path,
            {
                "schema": "conclave-package-inventory/0.1.0",
                "artifact": artifact.name,
                "members": scan["members"],
            },
        )
        for name in (n.lower() for n in scan["members"]):
            if any(marker in name for marker in FORBIDDEN_PACKAGE_MARKERS):
                package_findings.append(
                    f"PROHIBITED_PACKAGE_MEMBER:{artifact.name}:{name}"
                )
        scan_findings += [f"{artifact.name}:{finding}" for finding in scan["findings"]]
        packages.append(
            {
                "name": artifact.name,
                "content_hash": scan["content_hash"],
                "inventory_reference": inventory_path.name,
                "inventory_hash": digest(inventory_path),
                "member_count": scan["member_count"],
                "decompressed_bytes": scan["decompressed_bytes"],
            }
        )
    package_report = {
        "schema": "conclave-20d-package-report/0.1.0",
        "status": "PASS" if not package_findings else "FAIL",
        "packages": packages,
        "findings": sorted(package_findings),
    }
    secret_report = {
        "schema": SCANNER_VERSION,
        "status": "PASS" if not scan_findings else "FAIL",
        "scope": "bounded-decompressed-regular-package-members",
        "limits": {
            "members": MAX_ARCHIVE_MEMBERS,
            "member_bytes": MAX_MEMBER_BYTES,
            "aggregate_bytes": MAX_ARCHIVE_BYTES,
        },
        "packages": [
            {"name": p["name"], "content_hash": p["content_hash"]} for p in packages
        ],
        "findings": sorted(scan_findings),
    }
    test_report, static_report = (
        junit_report(args.junit, args.platform_id),
        static_scan(root),
    )
    emit(output / "package-report.json", package_report)
    emit(output / "secret-scan.json", secret_report)
    emit(output / "static-scan.json", static_report)
    emit(output / "test-report.json", test_report)
    validate_probe(args.probe.resolve(), digest(wheels[0]))
    expected_probe = output / "installed-wheel-probe.json"
    if args.probe.resolve() != expected_probe:
        expected_probe.write_bytes(args.probe.resolve().read_bytes())
    expected = {
        "package-report.json",
        "secret-scan.json",
        "static-scan.json",
        "test-report.json",
        "installed-wheel-probe.json",
        *(f"{p.name}.inventory.json" for p in artifacts),
    }
    reports = sorted(
        p for p in output.glob("*.json") if p.name != "evidence-index.json"
    )
    if {p.name for p in reports} != expected:
        raise ValueError("evidence output contains missing or unexpected JSON reports")
    emit(
        output / "evidence-index.json",
        {
            "schema": "conclave-20d-evidence-index/0.8.0",
            "platform_id": args.platform_id,
            "reports": [
                {"reference": p.name, "content_hash": digest(p)} for p in reports
            ],
        },
    )
    return (
        1
        if package_findings
        or scan_findings
        or static_report["status"] != "PASS"
        or test_report["status"] != "PASS"
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
