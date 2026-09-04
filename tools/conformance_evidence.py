"""Produce secret-free Increment 20D machine evidence from local build outputs.

The script performs no network operation and never reads environment values.
It inventories exact package bytes, inspects runtime source for prohibited
capability imports/calls, and binds the pytest machine report by SHA-256.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import tarfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

FORBIDDEN_PACKAGE_MARKERS = (
    "tests/", "test_", "fixture_broker", ".pem", ".key", ".p12", ".pfx",
    ".idmk", ".env", "token", "certificate",
)
RUNTIME_FILES = (
    "src/conclave/configuration.py",
    "src/conclave/sandbox_transport.py",
    "src/conclave/sandbox_recovery.py",
    "src/conclave/conformance.py",
)
TRANSPORT_FILES = RUNTIME_FILES[1:]
MAX_JUNIT_BYTES = 16 * 1024 * 1024
PLATFORM_IDS = {
    "windows-latest-py3.12",
    "ubuntu-latest-py3.13",
    "macos-latest-py3.12",
}
ALLOWED_SKIPS = {
    "windows-latest-py3.12": {
        "tests.test_configuration::test_symlink_profile_reference_is_rejected_when_supported",
        "tests.test_evidence::test_artifact_symlink_or_reparse_escape_is_refused",
    },
    "ubuntu-latest-py3.13": set(),
    "macos-latest-py3.12": set(),
}


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def emit(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def inventory(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return sorted(item.filename for item in archive.infolist() if not item.is_dir())
    with tarfile.open(path, "r:gz") as archive:
        return sorted(item.name for item in archive.getmembers() if item.isfile())


def static_scan(root: Path) -> dict:
    findings: list[str] = []
    forbidden_imports = {"cryptography", "jose", "nacl"}
    forbidden_calls = {"eval", "exec", "compile", "__import__"}
    for relative in RUNTIME_FILES:
        tree = ast.parse((root / relative).read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.split(".")[0] in forbidden_imports:
                        findings.append(f"FORBIDDEN_IMPORT:{relative}:{item.name}")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in forbidden_imports:
                    findings.append(f"FORBIDDEN_IMPORT:{relative}:{node.module}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in forbidden_calls:
                    findings.append(f"DYNAMIC_EXECUTION:{relative}:{node.func.id}")
    for relative in TRANSPORT_FILES:
        text = (root / relative).read_text(encoding="utf-8")
        if "import subprocess" in text or "import os.system" in text:
            findings.append(f"TRANSPORT_SHELL_SURFACE:{relative}")
    return {"schema": "conclave-20d-static-scan/0.1.0",
            "status": "PASS" if not findings else "FAIL", "findings": sorted(findings)}


def junit_report(path: Path, platform_id: str) -> dict:
    """Derive a secret-free status from bounded JUnit testcase outcomes."""
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

    failures = errors = 0
    skipped: list[str] = []
    for case in cases:
        failures += len(case.findall("failure"))
        errors += len(case.findall("error"))
        if case.find("skipped") is not None:
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            skipped.append(f"{classname}::{name}")
    allowed = ALLOWED_SKIPS[platform_id]
    unexpected = sorted(set(skipped) - allowed)
    allowed_observed = sorted(set(skipped) & allowed)
    reasons: list[str] = []
    if failures or errors:
        reasons.append("TEST_FAILURES_OR_ERRORS")
    if unexpected:
        reasons.append("UNEXPECTED_TEST_SKIP")
    status = "FAIL" if failures or errors else "NOT_RUN" if unexpected else "PASS"
    return {
        "schema": "conclave-20d-test-report/0.1.0",
        "status": status,
        "platform_id": platform_id,
        "tests": len(cases),
        "failures": failures,
        "errors": errors,
        "skipped": len(skipped),
        "allowed_skips_observed": allowed_observed,
        "unexpected_skips": unexpected,
        "reason_codes": reasons,
        "junit_reference": path.name,
        "junit_hash": digest(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform-id", required=True)
    args = parser.parse_args()
    root, dist, output = args.root.resolve(), args.dist.resolve(), args.output.resolve()
    if args.platform_id not in PLATFORM_IDS:
        raise SystemExit("unsupported 20D platform identifier")
    output.mkdir(parents=True, exist_ok=True)
    artifacts = sorted([*dist.glob("*.whl"), *dist.glob("*.tar.gz")])
    if len([p for p in artifacts if p.suffix == ".whl"]) != 1 or len(
        [p for p in artifacts if p.name.endswith(".tar.gz")]
    ) != 1:
        raise SystemExit("expected exactly one wheel and one sdist")

    packages = []
    package_findings = []
    secret_findings = []
    for artifact in artifacts:
        names = inventory(artifact)
        inventory_path = output / f"{artifact.name}.inventory.json"
        emit(inventory_path, {"schema": "conclave-package-inventory/0.1.0",
                              "artifact": artifact.name, "members": names})
        lowered = [name.lower() for name in names]
        for name in lowered:
            if any(marker in name for marker in FORBIDDEN_PACKAGE_MARKERS):
                package_findings.append(f"PROHIBITED_PACKAGE_MEMBER:{artifact.name}:{name}")
        raw = artifact.read_bytes()
        if b"-----BEGIN PRIVATE KEY-----" in raw or b"-----BEGIN RSA PRIVATE KEY-----" in raw:
            secret_findings.append(f"PRIVATE_KEY_SENTINEL:{artifact.name}")
        packages.append({"name": artifact.name, "content_hash": digest(artifact),
                         "inventory_reference": inventory_path.name,
                         "inventory_hash": digest(inventory_path)})

    package_report = {"schema": "conclave-20d-package-report/0.1.0",
                      "status": "PASS" if not package_findings else "FAIL",
                      "packages": packages, "findings": sorted(package_findings)}
    secret_report = {"schema": "conclave-20d-secret-scan/0.1.0",
                     "status": "PASS" if not secret_findings else "FAIL",
                     "scope": "built-sdist-and-wheel-exact-bytes",
                     "findings": sorted(secret_findings)}
    test_report = junit_report(args.junit, args.platform_id)
    emit(output / "package-report.json", package_report)
    emit(output / "secret-scan.json", secret_report)
    emit(output / "static-scan.json", static_scan(root))
    emit(output / "test-report.json", test_report)
    reports = sorted(output.glob("*.json"))
    emit(output / "evidence-index.json", {
        "schema": "conclave-20d-evidence-index/0.1.0",
        "platform_id": args.platform_id,
        "reports": [{"reference": p.name, "content_hash": digest(p)} for p in reports],
    })
    return 1 if (
        package_findings or secret_findings or static_scan(root)["status"] != "PASS"
        or test_report["status"] != "PASS"
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
